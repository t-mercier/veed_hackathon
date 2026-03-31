"""Supabase client for updating video_requests status via REST API."""

import logging
from typing import Optional

import httpx

from config import settings

import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _sb_headers() -> dict:
    """Supabase PostgREST headers using service role key."""
    load_dotenv()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def update_request_status(
    request_id: str,
    status: str,
    video_url: Optional[str] = None,
    error: Optional[str] = None,
    backend_job_id: Optional[str] = None,
    job_type: Optional[str] = None,
) -> None:
    """Update a video_requests row in Supabase via PostgREST."""
    if not settings.supabase_url or not request_id:
        return
    url = f"{settings.supabase_url}/rest/v1/video_requests?id=eq.{request_id}"
    headers = _sb_headers()

    data: dict = {"status": status}
    if error is not None:
        data["error_message"] = error  # column is error_message, not error
    if backend_job_id is not None:
        data["backend_job_id"] = backend_job_id
    if job_type is not None:
        data["job_type"] = job_type

    try:
        resp = httpx.patch(url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info("[supabase] Updated request %s → %s", request_id, status)
    except Exception as exc:
        logger.error("[supabase] Failed to update request %s: %s", request_id, exc)

    # For completed code jobs, also insert into generated_videos
    if status == "completed" and video_url:
        _insert_generated_video(request_id, video_url)


def _insert_generated_video(request_id: str, video_url: str) -> None:
    """Insert a row into generated_videos so the frontend can find the result."""
    url = f"{settings.supabase_url}/rest/v1/generated_videos"
    headers = _sb_headers()

    # We need the user_id from the request — fetch it first
    req_url = f"{settings.supabase_url}/rest/v1/video_requests?id=eq.{request_id}&select=user_id"
    try:
        resp = httpx.get(req_url, headers={**headers, "Prefer": ""}, timeout=10)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            logger.warning("[supabase] No video_request found for %s, skipping generated_videos insert", request_id)
            return
        user_id = rows[0]["user_id"]
    except Exception as exc:
        logger.error("[supabase] Failed to fetch user_id for request %s: %s", request_id, exc)
        return

    data = {
        "request_id": request_id,
        "user_id": user_id,
        "video_url": video_url,
    }
    try:
        resp = httpx.post(url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info("[supabase] Inserted generated_video for request %s", request_id)
    except Exception as exc:
        logger.error("[supabase] Failed to insert generated_video for %s: %s", request_id, exc)
