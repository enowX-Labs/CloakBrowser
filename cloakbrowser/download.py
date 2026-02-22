"""Binary download and cache management for cloakbrowser.

Downloads the patched Chromium binary on first use, caches it locally.
Similar to how Playwright downloads its own bundled Chromium.
"""

from __future__ import annotations

import logging
import os
import stat
import tarfile
import tempfile
from pathlib import Path

import httpx

from .config import (
    CHROMIUM_VERSION,
    get_binary_dir,
    get_binary_path,
    get_download_url,
    get_local_binary_override,
    get_platform_tag,
)

logger = logging.getLogger("cloakbrowser")

# Timeout for download (large binary, allow 10 min)
DOWNLOAD_TIMEOUT = 600.0


def ensure_binary() -> str:
    """Ensure the stealth Chromium binary is available. Download if needed.

    Returns the path to the chrome executable as a string.

    Set CLOAKBROWSER_BINARY_PATH to skip download and use a local build.
    """
    # Check for local override first
    local_override = get_local_binary_override()
    if local_override:
        path = Path(local_override)
        if not path.exists():
            raise FileNotFoundError(
                f"CLOAKBROWSER_BINARY_PATH set to '{local_override}' but file does not exist"
            )
        logger.info("Using local binary override: %s", local_override)
        return str(path)

    # Check if binary is already cached
    binary_path = get_binary_path()
    if binary_path.exists() and _is_executable(binary_path):
        logger.debug("Binary found in cache: %s", binary_path)
        return str(binary_path)

    # Download
    logger.info(
        "Stealth Chromium %s not found. Downloading for %s...",
        CHROMIUM_VERSION,
        get_platform_tag(),
    )
    _download_and_extract()

    if not binary_path.exists():
        raise RuntimeError(
            f"Download completed but binary not found at expected path: {binary_path}. "
            f"This may indicate a packaging issue. Please report at "
            f"https://github.com/CloakHQ/cloakbrowser/issues"
        )

    return str(binary_path)


def _download_and_extract() -> None:
    """Download the binary archive and extract to cache directory."""
    url = get_download_url()
    binary_dir = get_binary_dir()

    # Create cache dir
    binary_dir.parent.mkdir(parents=True, exist_ok=True)

    # Download to temp file first (atomic — no partial downloads in cache)
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        _download_file(url, tmp_path)
        _extract_archive(tmp_path, binary_dir)
    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


def _download_file(url: str, dest: Path) -> None:
    """Download a file with progress logging."""
    logger.info("Downloading from %s", url)

    with httpx.stream("GET", url, follow_redirects=True, timeout=DOWNLOAD_TIMEOUT) as response:
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        last_logged_pct = -1

        with open(dest, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

                if total > 0:
                    pct = int(downloaded / total * 100)
                    # Log every 10%
                    if pct >= last_logged_pct + 10:
                        last_logged_pct = pct
                        logger.info(
                            "Download progress: %d%% (%d/%d MB)",
                            pct,
                            downloaded // (1024 * 1024),
                            total // (1024 * 1024),
                        )

    logger.info("Download complete: %d MB", dest.stat().st_size // (1024 * 1024))


def _extract_archive(archive_path: Path, dest_dir: Path) -> None:
    """Extract tar.gz archive to destination directory."""
    logger.info("Extracting to %s", dest_dir)

    # Clean existing dir if partial download existed
    if dest_dir.exists():
        import shutil
        shutil.rmtree(dest_dir)

    dest_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as tar:
        # Security: prevent path traversal and symlink attacks
        safe_members = []
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                logger.warning("Skipping symlink in archive: %s", member.name)
                continue
            member_path = (dest_dir / member.name).resolve()
            if not str(member_path).startswith(str(dest_dir.resolve())):
                raise RuntimeError(f"Archive contains path traversal: {member.name}")
            safe_members.append(member)

        tar.extractall(dest_dir, members=safe_members)

    # If tar extracted into a single subdirectory, flatten it
    # (e.g. fingerprint-chromium-142-custom-v2/chrome → chrome)
    _flatten_single_subdir(dest_dir)

    # Make binary executable
    binary_path = get_binary_path()
    if binary_path.exists():
        _make_executable(binary_path)
        logger.info("Binary ready: %s", binary_path)


def _flatten_single_subdir(dest_dir: Path) -> None:
    """If extraction created a single subdirectory, move its contents up.

    Many tar archives wrap files in a top-level directory (e.g.
    fingerprint-chromium-142-custom-v2/chrome). We want chrome at dest_dir/chrome.
    """
    import shutil

    entries = list(dest_dir.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        subdir = entries[0]
        logger.debug("Flattening single subdirectory: %s", subdir.name)
        for item in subdir.iterdir():
            shutil.move(str(item), str(dest_dir / item.name))
        subdir.rmdir()


def _is_executable(path: Path) -> bool:
    """Check if a file is executable."""
    return os.access(path, os.X_OK)


def _make_executable(path: Path) -> None:
    """Make a file executable (chmod +x)."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def clear_cache() -> None:
    """Remove all cached binaries. Forces re-download on next launch."""
    from .config import get_cache_dir
    import shutil

    cache_dir = get_cache_dir()
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        logger.info("Cache cleared: %s", cache_dir)


def binary_info() -> dict:
    """Return info about the current binary installation."""
    binary_path = get_binary_path()
    return {
        "version": CHROMIUM_VERSION,
        "platform": get_platform_tag(),
        "binary_path": str(binary_path),
        "installed": binary_path.exists(),
        "cache_dir": str(get_binary_dir()),
        "download_url": get_download_url(),
    }
