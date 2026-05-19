from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import time

import requests
import yt_dlp

from ..sanitize import sanitize_text
from ..sources import SourceConfig
from ..youtube import extract_video_id


FORMAT_CANDIDATES = (
    "bestvideo[height<=1080]+bestaudio/bestvideo*[height<=1080]+bestaudio/best",
    "bestvideo+bestaudio/best",
    "bv*+ba/b",
    "best",
)

SIGN_IN_ERRORS = (
    "Sign in to confirm",
    "Requested format is not available",
    "bot",
    "login",
    "Please sign in",
)

DEFAULT_EXTRACTOR_ARGS = {
    "youtube": {
        "skip": ["dash", "hls"],  # skip DASH/HLS manifest check to avoid bot detection
    },
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _bootstrap_bilibili_cookie(cookie_path: Path) -> None:
    response = requests.get(
        "https://www.bilibili.com/",
        headers={"User-Agent": DEFAULT_USER_AGENT, "Referer": "https://www.bilibili.com/"},
        timeout=10,
    )
    response.raise_for_status()
    expires = int(time.time()) + 3600 * 24 * 365
    lines = ["# Netscape HTTP Cookie File", ""]
    cookies = dict(response.cookies)
    cookies.setdefault("SESSDATA", "anonymous_for_webpage_playinfo")
    for name, value in cookies.items():
        lines.append("\t".join([".bilibili.com", "TRUE", "/", "FALSE", str(expires), name, value]))
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    cookie_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _proxy_url(proxy_port: str = "") -> str:
    if proxy_port.strip():
        return f"http://127.0.0.1:{proxy_port.strip()}"
    return os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or ""


def _ensure_cookie(source: SourceConfig) -> None:
    cookie_path = source.cookie_path
    if not cookie_path or source.name != "bilibili":
        return
    if cookie_path.exists() and cookie_path.stat().st_size > 0:
        return
    _bootstrap_bilibili_cookie(cookie_path)


def _ydl_base(source: SourceConfig, proxy_port: str = "") -> dict[str, Any]:
    opts: dict[str, Any] = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {}},
        "http_headers": {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
        "extractor_args": DEFAULT_EXTRACTOR_ARGS,
        "extractor_retries": 5,
    }
    cookie_path = source.cookie_path
    if cookie_path and cookie_path.exists() and cookie_path.stat().st_size > 0:
        opts["cookiefile"] = str(cookie_path)
    if not source.use_proxy:
        opts["proxy"] = ""
        return opts
    proxy = _proxy_url(proxy_port)
    if proxy:
        opts["proxy"] = proxy
    return opts


def _session_path(workfolder: Path, info: dict[str, Any]) -> Path:
    uploader = sanitize_text(str(info.get("uploader") or "unknown"))
    title = sanitize_text(str(info.get("title") or "untitled"))
    video_id = str(info.get("id") or extract_video_id(str(info.get("webpage_url") or "")))
    return workfolder / uploader / f"{title}__{video_id}"


def _is_sign_in_required(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(err.lower() in msg for err in SIGN_IN_ERRORS)


def _remove_partial_outputs(video_file: Path) -> None:
    for candidate in video_file.parent.glob(f"{video_file.name}*"):
        if candidate == video_file:
            continue
        if candidate.is_file():
            candidate.unlink(missing_ok=True)


def _find_cached_session(workfolder: Path, video_id: str) -> list[Path]:
    if not workfolder.is_dir():
        return []
    sessions = []
    for sub in workfolder.iterdir():
        if not sub.is_dir():
            continue
        for session_dir in sub.iterdir():
            if not session_dir.is_dir():
                continue
            if f"__{video_id}" in session_dir.name:
                metadata_file = session_dir / "metadata" / "ytdlp_info.json"
                video_file = session_dir / "media" / "video_source.mp4"
                if metadata_file.exists() and video_file.exists() and video_file.stat().st_size > 0:
                    sessions.append(session_dir)
    return sessions


def _download_with_format_candidates(
    url: str, video_file: Path, source: SourceConfig, proxy_port: str
) -> None:
    last_error: Exception | None = None
    for format_selector in FORMAT_CANDIDATES:
        download_opts = {
            **_ydl_base(source, proxy_port),
            "format": format_selector,
            "merge_output_format": "mp4",
            "outtmpl": str(video_file),
            "retries": 10,
            "fragment_retries": 10,
        }
        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([url])
            return
        except Exception as exc:
            last_error = exc
            _remove_partial_outputs(video_file)
            if _is_sign_in_required(exc):
                continue
    if last_error:
        msg = str(last_error)
        if _is_sign_in_required(last_error):
            raise RuntimeError(
                "YouTube requires authentication for this video. "
                "Please update your YouTube cookie in Settings → YouTube Cookie, "
                "then try again."
            ) from last_error
        raise last_error


def download_video(
    url: str, workfolder: Path, source: SourceConfig, proxy_port: str = ""
) -> tuple[Path, dict[str, Any]]:
    video_id = extract_video_id(url)

    # Fast path: if video already downloaded and metadata cached, skip yt-dlp entirely.
    candidate_sessions = _find_cached_session(workfolder, video_id)
    if candidate_sessions:
        session = candidate_sessions[0]
        video_file = session / "media" / "video_source.mp4"
        metadata_file = session / "metadata" / "ytdlp_info.json"
        if video_file.exists() and video_file.stat().st_size > 0:
            info = json.loads(metadata_file.read_text(encoding="utf-8"))
            return session, info

    _ensure_cookie(source)
    info_opts = _ydl_base(source, proxy_port)
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if str(info.get("id", video_id)) != video_id:
        raise ValueError("The resolved video id does not match the submitted URL.")

    session = _session_path(workfolder, info)
    media_dir = session / "media"
    metadata_dir = session / "metadata"
    media_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    video_file = media_dir / "video_source.mp4"
    metadata_file = metadata_dir / "ytdlp_info.json"
    metadata_file.write_text(json.dumps(ydl.sanitize_info(info), ensure_ascii=False, indent=2), encoding="utf-8")

    if video_file.exists() and video_file.stat().st_size > 0:
        return session, info

    _download_with_format_candidates(url, video_file, source, proxy_port)

    if not video_file.exists() or video_file.stat().st_size == 0:
        raise RuntimeError("yt-dlp finished without producing media/video_source.mp4")

    return session, info
