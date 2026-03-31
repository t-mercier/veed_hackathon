"""
URL / GitHub repo enrichment.

Fetches relevant content from a URL or GitHub repo and returns a concise
summary to prepend to the prompt.
"""

import base64
import re
import httpx
from bs4 import BeautifulSoup


_GITHUB_REPO_RE = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/\s]+)"
)

# Root-level files worth fetching for context
_KEY_ENTRY_FILES = {
    "main.py", "app.py", "server.py",
    "index.ts", "index.js", "App.tsx", "App.jsx", "index.tsx",
}

_GH_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "explainer-bot/1.0",
}


def _gh_headers() -> dict:
    """Return GitHub API headers, including auth token if available."""
    from config import settings
    headers = dict(_GH_HEADERS)
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def ingest_github_repo(url: str) -> str:
    """
    Build a structured repo summary via the GitHub API (no key needed for public repos).

    Returns a text block covering: directory structure, key entry-point files,
    and a README excerpt. Suitable as Mistral context (~3–5k chars).

    Raises:
        ValueError: if the URL is not a github.com URL.
        httpx.HTTPStatusError: if the repo returns a non-2xx (e.g. 404).
    """
    m = _GITHUB_REPO_RE.match(url.strip())
    if not m:
        raise ValueError(f"Expected a github.com URL, got: {url!r}")

    owner, repo = m.group("owner"), m.group("repo")

    async with httpx.AsyncClient(timeout=20) as client:
        tree_text = await _fetch_tree_summary(client, owner, repo)
        readme_text = await _fetch_readme(client, owner, repo)
        key_files_text = await _fetch_key_files(client, owner, repo)

    parts = [f"=== Repository: {owner}/{repo} ==="]
    if tree_text:
        parts.append(f"Directory structure:\n{tree_text}")
    if key_files_text:
        parts.append(f"Key source files:\n{key_files_text}")
    if readme_text:
        parts.append(f"README (excerpt):\n{readme_text[:1200]}")

    return "\n\n".join(parts)


async def _fetch_tree_summary(client: httpx.AsyncClient, owner: str, repo: str) -> str:
    """Return a two-column directory listing (root files + top-level dirs with counts)."""
    for ref in ("HEAD", "main", "master"):
        try:
            r = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}",
                params={"recursive": "1"},
                headers=_gh_headers(),
            )
            if r.status_code == 200:
                break
        except Exception:
            continue
    else:
        return ""

    items = r.json().get("tree", [])
    dir_counts: dict[str, int] = {}
    root_files: list[str] = []

    for item in items:
        if item.get("type") != "blob":
            continue
        parts = item["path"].split("/")
        if len(parts) == 1:
            root_files.append(parts[0])
        else:
            top = parts[0]
            dir_counts[top] = dir_counts.get(top, 0) + 1

    lines = [f"  {f}" for f in sorted(root_files)[:10]]
    lines += [
        f"  {d}/  ({count} files)"
        for d, count in sorted(dir_counts.items(), key=lambda x: -x[1])[:12]
    ]
    return "\n".join(lines)


async def _fetch_readme(client: httpx.AsyncClient, owner: str, repo: str) -> str:
    try:
        r = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/readme",
            headers=_gh_headers(),
        )
        if r.status_code == 200:
            content = r.json().get("content", "")
            return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""


async def _fetch_key_files(client: httpx.AsyncClient, owner: str, repo: str) -> str:
    try:
        r = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents",
            headers=_gh_headers(),
        )
        if r.status_code != 200 or not isinstance(r.json(), list):
            return ""
    except Exception:
        return ""

    to_fetch = [
        item["download_url"]
        for item in r.json()
        if item.get("type") == "file" and item.get("name") in _KEY_ENTRY_FILES
    ][:2]

    parts = []
    for file_url in to_fetch:
        try:
            r = await client.get(file_url, headers={"User-Agent": "explainer-bot/1.0"})
            if r.status_code == 200:
                name = file_url.split("/")[-1]
                parts.append(f"--- {name} ---\n{r.text[:1500]}")
        except Exception:
            pass

    return "\n\n".join(parts)


async def enrich_prompt(prompt: str, url: str | None) -> str:
    """Return enriched prompt. If no URL, returns prompt unchanged."""
    if not url:
        return prompt

    context = await _fetch_context(url.strip())
    if not context:
        return prompt

    return f"{prompt}\n\n--- Context from {url} ---\n{context}"


async def _fetch_context(url: str) -> str:
    m = _GITHUB_REPO_RE.match(url)
    if m:
        return await _fetch_github_repo(m.group("owner"), m.group("repo"))
    return await _fetch_webpage(url)


async def _fetch_github_repo(owner: str, repo: str) -> str:
    """Lightweight repo context for the code-snippet enrichment path.
    Reuses the authenticated helpers from the repo pipeline."""
    url = f"https://github.com/{owner}/{repo}"
    try:
        return await ingest_github_repo(url)
    except Exception:
        return ""


async def _fetch_webpage(url: str) -> str:
    """Fetch and extract readable text from a webpage."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; explainer-bot/1.0)"},
            )
            r.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines[:150])
