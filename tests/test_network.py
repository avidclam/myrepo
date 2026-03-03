"""Tests for network utilities."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import requests

from myrepo.network import download_url, _extract_filename


class TestDownloadUrl:
    """Tests for download_url function."""

    def test_empty_url_raises_value_error(self):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            download_url("", "output.txt")

        with pytest.raises(ValueError, match="URL cannot be empty"):
            download_url("   ", "output.txt")

    def test_http_error_raises_requests_http_error(self):
        """Test that HTTP errors are raised properly."""
        with patch("myrepo.network.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.HTTPError(
                "404 Not Found"
            )
            mock_get.return_value = mock_response

            with pytest.raises(requests.HTTPError):
                download_url("https://example.com/notfound", "output.txt")

    def test_successful_download_writes_correct_content(self, tmp_path):
        """Test that successful download writes correct content to file."""
        test_content = b"Hello, World! This is test content."
        url = "https://example.com/test.txt"
        dest = tmp_path / "output.txt"

        with patch("myrepo.network.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.headers = {"content-length": str(len(test_content))}
            mock_response.iter_content.return_value = [test_content]
            mock_get.return_value = mock_response

            result = download_url(url, dest, show_progress=False)

            assert result == dest
            assert dest.exists()
            assert dest.read_bytes() == test_content

    def test_download_to_directory_uses_url_filename(self, tmp_path):
        """Test that downloading to a directory extracts filename from URL."""
        test_content = b"test data"
        url = "https://example.com/path/to/myfile.csv"
        dest_dir = tmp_path / "downloads"
        dest_dir.mkdir()

        with patch("myrepo.network.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.headers = {}
            mock_response.iter_content.return_value = [test_content]
            mock_get.return_value = mock_response

            result = download_url(url, dest_dir, show_progress=False)

            assert result == dest_dir / "myfile.csv"
            assert result.exists()
            assert result.read_bytes() == test_content

    def test_atomic_save_uses_temp_file(self, tmp_path):
        """Test that download uses temporary .part file during download."""
        test_content = b"atomic test"
        url = "https://example.com/file.bin"
        dest = tmp_path / "output.bin"
        temp_file = tmp_path / "output.bin.part"

        with patch("myrepo.network.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.headers = {}
            mock_response.iter_content.return_value = [test_content]
            mock_get.return_value = mock_response

            # Track if temp file was created
            original_open = open

            def tracking_open(path, *args, **kwargs):
                p = Path(path)
                if p == temp_file and "wb" in args:
                    # Temp file should be created
                    assert not dest.exists(), "Final file should not exist yet"
                return original_open(path, *args, **kwargs)

            with patch("builtins.open", side_effect=tracking_open):
                result = download_url(url, dest, show_progress=False)

            # After successful download, temp file should be gone
            assert not temp_file.exists()
            assert dest.exists()
            assert result == dest

    def test_cleanup_temp_file_on_error(self, tmp_path):
        """Test that temporary file is cleaned up on download error."""
        url = "https://example.com/file.bin"
        dest = tmp_path / "output.bin"
        temp_file = tmp_path / "output.bin.part"

        with patch("myrepo.network.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.headers = {}
            # Simulate error during download
            mock_response.iter_content.side_effect = IOError("Network error")
            mock_get.return_value = mock_response

            with pytest.raises(IOError):
                download_url(url, dest, show_progress=False)

            # Temp file should be cleaned up
            assert not temp_file.exists()
            assert not dest.exists()

    def test_chunked_download(self, tmp_path):
        """Test that download processes content in chunks."""
        chunk1 = b"chunk1"
        chunk2 = b"chunk2"
        chunk3 = b"chunk3"
        url = "https://example.com/chunked.bin"
        dest = tmp_path / "output.bin"

        with patch("myrepo.network.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.headers = {}
            mock_response.iter_content.return_value = [chunk1, chunk2, chunk3]
            mock_get.return_value = mock_response

            result = download_url(url, dest, show_progress=False, chunk_size=1024)

            assert dest.read_bytes() == chunk1 + chunk2 + chunk3
            # Verify iter_content was called with correct chunk_size
            mock_response.iter_content.assert_called_once_with(chunk_size=1024)

    def test_progress_bar_disabled_when_show_progress_false(self, tmp_path):
        """Test that progress bar is not shown when show_progress=False."""
        test_content = b"no progress"
        url = "https://example.com/file.txt"
        dest = tmp_path / "output.txt"

        with patch("myrepo.network.requests.get") as mock_get:
            with patch("myrepo.network.tqdm") as mock_tqdm:
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None
                mock_response.headers = {"content-length": "11"}
                mock_response.iter_content.return_value = [test_content]
                mock_get.return_value = mock_response

                download_url(url, dest, show_progress=False)

                # tqdm should not be called
                mock_tqdm.assert_not_called()


class TestExtractFilename:
    """Tests for _extract_filename helper function."""

    def test_extract_from_url_path(self):
        """Test extracting filename from URL path."""
        url = "https://example.com/path/to/document.pdf"
        response = Mock()
        response.headers = {}

        filename = _extract_filename(url, response)
        assert filename == "document.pdf"

    def test_extract_from_content_disposition(self):
        """Test extracting filename from Content-Disposition header."""
        url = "https://example.com/download"
        response = Mock()
        response.headers = {"content-disposition": 'attachment; filename="report.xlsx"'}

        filename = _extract_filename(url, response)
        assert filename == "report.xlsx"

    def test_content_disposition_takes_precedence(self):
        """Test that Content-Disposition takes precedence over URL."""
        url = "https://example.com/download/file.txt"
        response = Mock()
        response.headers = {"content-disposition": 'attachment; filename="actual.csv"'}

        filename = _extract_filename(url, response)
        assert filename == "actual.csv"

    def test_url_encoded_filename(self):
        """Test handling of URL-encoded filenames."""
        url = "https://example.com/my%20file%20name.txt"
        response = Mock()
        response.headers = {}

        filename = _extract_filename(url, response)
        assert filename == "my file name.txt"

    def test_default_filename_when_none_found(self):
        """Test default filename when none can be extracted."""
        url = "https://example.com/"
        response = Mock()
        response.headers = {}

        filename = _extract_filename(url, response)
        assert filename == "downloaded_file"
