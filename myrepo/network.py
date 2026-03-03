"""Network utilities for downloading files."""

import logging
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests
from tqdm.auto import tqdm

logger = logging.getLogger(__name__)


def download_url(
    url: str,
    dest: str | Path,
    *,
    show_progress: bool | None = None,
    chunk_size: int = 1024 * 128,
) -> Path:
    """Download file from URL and save it atomically to dest.

    Downloads a file from the given URL with optional progress indication and
    saves it atomically by first writing to a temporary file, then renaming
    to the final destination only after successful download.

    Args:
        url: HTTP/HTTPS URL to download from.
        dest: Destination path. If a directory, the filename will be detected
            from the URL or Content-Disposition header. If a file path, that
            exact name will be used.
        show_progress: Whether to show a progress bar. If None (default),
            automatically detects terminal vs Jupyter environment. Set to False
            to disable progress indication.
        chunk_size: Size of chunks to download at a time in bytes.
            Default is 128 KiB.

    Returns:
        Path object pointing to the downloaded file.

    Raises:
        ValueError: If url is empty or invalid.
        requests.HTTPError: If the HTTP request fails (non-200 status).
        requests.RequestException: For other network-related errors.

    Examples:
        >>> # Download to specific file
        >>> download_url("https://example.com/file.zip", "myfile.zip")
        PosixPath('myfile.zip')

        >>> # Download to directory (filename auto-detected)
        >>> download_url("https://example.com/data.csv", "downloads/")
        PosixPath('downloads/data.csv')

        >>> # Disable progress bar
        >>> download_url("https://example.com/file.bin", "file.bin",
        ...              show_progress=False)
        PosixPath('file.bin')
    """
    if not url or not url.strip():
        raise ValueError("URL cannot be empty")

    dest_path = Path(dest)

    # Start the download with streaming
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
    except requests.HTTPError:
        raise
    except requests.RequestException as e:
        logger.error(f"Failed to download from {url}: {e}")
        raise

    # Determine final filename
    if dest_path.is_dir():
        filename = _extract_filename(url, response)
        final_path = dest_path / filename
    else:
        final_path = dest_path

    # Ensure parent directory exists
    final_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file path
    temp_path = final_path.with_suffix(final_path.suffix + ".part")

    try:
        # Get total size if available
        total_size = int(response.headers.get("content-length", 0))

        # Determine if we should show progress
        use_progress = show_progress if show_progress is not None else True

        # Download with progress bar
        with open(temp_path, "wb") as f:
            if use_progress and total_size > 0:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=final_path.name,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            elif use_progress:
                # No content-length, show indeterminate progress
                with tqdm(
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=final_path.name,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                # No progress bar
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

        # Atomic rename: only after successful download
        temp_path.rename(final_path)
        logger.info(f"Successfully downloaded {url} to {final_path}")
        return final_path

    except Exception as e:
        # Clean up temporary file on any error
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Download failed, cleaned up temporary file: {e}")
        raise


def _extract_filename(url: str, response: requests.Response) -> str:
    """Extract filename from URL or Content-Disposition header.

    Args:
        url: The URL being downloaded.
        response: The HTTP response object.

    Returns:
        Extracted filename as a string.
    """
    # Try Content-Disposition header first
    content_disp = response.headers.get("content-disposition", "")
    if content_disp and "filename=" in content_disp:
        # Parse filename from Content-Disposition
        parts = content_disp.split("filename=")
        if len(parts) > 1:
            filename = parts[1].strip().strip('"').strip("'")
            if filename:
                return filename

    # Fall back to URL path
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = path.split("/")[-1]

    # If still no filename, use a default
    if not filename or filename == "":
        filename = "downloaded_file"

    return filename
