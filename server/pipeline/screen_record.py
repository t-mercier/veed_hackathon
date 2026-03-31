"""
Captures the React Flow explainer player as a video using Playwright.
Navigates to the running frontend, clicks "Start Explanation",
waits for playback to complete, and saves the recording as final.mp4.
"""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

FRONTEND_BASE = "http://localhost:5173"


async def _record(url: str, out_mp4: Path, timeout_ms: int = 600_000) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 854, "height": 480 + 80},  # +80 for navbar
            record_video_dir=str(out_mp4.parent),
            record_video_size={"width": 854, "height": 560},
        )
        page = await ctx.new_page()

        # Grant autoplay permissions
        await ctx.grant_permissions(["camera", "microphone"])

        logger.info("Navigating to %s", url)
        await page.goto(url, wait_until="networkidle", timeout=30_000)

        # Click "Start Explanation" button
        try:
            await page.click("text=Start Explanation", timeout=10_000)
            logger.info("Clicked 'Start Explanation'")
        except Exception:
            logger.warning("No 'Start Explanation' button found — recording anyway")

        # Wait for the video/player to finish
        # We detect end by waiting for "Watch again" button or a done state
        try:
            await page.wait_for_selector(
                "text=Watch again", timeout=timeout_ms
            )
            logger.info("Playback complete (detected 'Watch again')")
        except Exception:
            logger.warning("Timed out waiting for playback end — stopping recording")

        # Give it a moment to settle
        await asyncio.sleep(1)

        await ctx.close()
        await browser.close()

    # Playwright saves video as a temp .webm in the dir — find and convert it
    webms = sorted(out_mp4.parent.glob("*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not webms:
        raise FileNotFoundError("Playwright did not save a recording")

    webm = webms[0]
    logger.info("Converting %s → %s", webm.name, out_mp4.name)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(webm),
         "-c:v", "libx264", "-preset", "fast", "-crf", "23",
         "-c:a", "aac", "-b:a", "128k",
         "-pix_fmt", "yuv420p",
         str(out_mp4)],
        capture_output=True, text=True, close_fds=True, stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed:\n{result.stderr[-500:]}")

    webm.unlink(missing_ok=True)
    logger.info("Done → %s", out_mp4)


def record_explainer(job_id: str, job_type: str, out_mp4: Path,
                     frontend_base: str = FRONTEND_BASE) -> Path:
    """
    Synchronous wrapper. job_type: 'repo' | 'prompt' | 'concept_algo'
    """
    route = {
        "repo":         f"/repo/{job_id}",
        "prompt":       f"/prompt/{job_id}",
        "concept_algo": f"/concept/{job_id}",
    }.get(job_type, f"/prompt/{job_id}")

    url = f"{frontend_base}{route}"
    asyncio.run(_record(url, out_mp4))
    return out_mp4
