# feat: implement file downloader `download_url` in `myrepo/network.py` with progress bar and atomic save

## Goal

Create a reliable progress-indicating function to download files (including very large ones) from HTTP/HTTPS URLs. Provide full docstring in Google format.

The function should:
- show nice progress bar (automatic detection: terminal vs Jupyter)
- save file **atomically** (temporary name → final name only after successful download)
- stream download in chunks (don't load entire file into memory)

## Desired public API

```python
from myrepo.network import download_url

download_url(
    url: str,
    dest: str | Path,  # where to save final file
    *,
    show_progress: bool | None = None,  # None = auto-detect
    chunk_size: int = 1024 * 128,  # 128 KiB default
) -> Path:
    """Download file from URL and save it atomically to dest.
    """
```

## Requirements / must-have

### Progress bar
- Use tqdm when possible, unless show_progress = False
- Automatic detection: terminal → classic tqdm bar, Jupyter → notebook-friendly progress
- Show total size if Content-Length is present

### Atomic save / safe overwrite
- Download to temporary file in the same directory (.part suffix)
- Only rename to final name after complete download
- If interrupted / failed → remove temporary file (untill resume feature is requested in the future)

### Filename handling
- If dest is directory → save with filename detected from URL or from Content-Disposition
- If dest is file → use exactly this name

### Error handling
- Raise `ValueError` for empty URL
- Raise `requests.HTTPError` for non-200 responses  
- Always clean up `.part` file on any exception

## Tests
- Mock all network calls
- Test: successful download writes correct content
- Test: empty URL raises ValueError
- Test: HTTP error raises requests.HTTPError

## Out of scope for this version
- resumable downloads (Range requests)
- multi-connection / parallel chunks
- async operations

