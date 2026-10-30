from pathlib import Path
from typing import cast

import pytest
from aiohttp import FormData
from aioresponses import CallbackResult, aioresponses
from yarl import URL

from mcp_tracker.tracker.custom.client import TrackerClient
from mcp_tracker.tracker.custom.errors import (
    IssueNotFound,
    TrackerAPIError,
    TrackerAPITimeout,
)
from mcp_tracker.tracker.proto.common import YandexAuth


@pytest.mark.parametrize("temporary", [False, True])
async def test_upload_multipart_bytes_and_auth(
    tracker_client: TrackerClient,
    tmp_path: Path,
    yandex_auth: YandexAuth,
    temporary: bool,
) -> None:
    path = tmp_path / "report.bin"
    path.write_bytes(b"\x00report\xff\r\n")
    endpoint = "v3/attachments" if temporary else "v3/issues/TEST-123/attachments"

    async def capture(url: URL, **kwargs: object) -> CallbackResult:
        form = kwargs["data"]
        assert isinstance(form, FormData)
        multipart = form()
        assert multipart.content_type.startswith("multipart/form-data; boundary=")
        body = await multipart.as_bytes()
        assert b'name="file"; filename="report.bin"' in body
        assert b"\r\n\r\n\x00report\xff\r\n\r\n" in body
        headers = cast(dict[str, str], kwargs["headers"])
        assert headers["Authorization"] == "OAuth auth-token"
        assert headers["X-Org-ID"] == "auth-org"
        assert "Content-Type" not in headers
        assert kwargs.get("json") is None
        return CallbackResult(
            status=201, payload={"id": "42", "name": "report.bin", "size": 10}
        )

    with aioresponses() as mock:
        mock.post(f"https://api.tracker.yandex.net/{endpoint}", callback=capture)
        result = await tracker_client.issue_add_attachment(
            "TEST-123", str(path), temporary=temporary, auth=yandex_auth
        )
    assert result.id == "42"
    assert result.name == "report.bin"


@pytest.mark.parametrize("kind", ["relative", "missing", "directory"])
async def test_invalid_file_never_sends_request(
    tracker_client: TrackerClient, tmp_path: Path, kind: str
) -> None:
    path = {
        "relative": Path("report.txt"),
        "missing": tmp_path / "missing",
        "directory": tmp_path,
    }[kind]
    with aioresponses() as mock:
        with pytest.raises(ValueError, match="absolute path to a regular file"):
            await tracker_client.issue_add_attachment("TEST-123", str(path))
        assert not mock.requests


@pytest.mark.parametrize(
    ("temporary", "status", "error"),
    [
        (False, 404, IssueNotFound),
        (True, 404, TrackerAPIError),
        (False, 413, TrackerAPIError),
    ],
)
async def test_upload_api_errors(
    tracker_client: TrackerClient,
    tmp_path: Path,
    temporary: bool,
    status: int,
    error: type[Exception],
) -> None:
    path = tmp_path / "report.txt"
    path.write_text("report")
    endpoint = "v3/attachments" if temporary else "v3/issues/TEST-123/attachments"
    with aioresponses() as mock:
        mock.post(f"https://api.tracker.yandex.net/{endpoint}", status=status)
        with pytest.raises(error):
            await tracker_client.issue_add_attachment(
                "TEST-123", str(path), temporary=temporary
            )
    # The file handle is released even when Tracker rejects the upload (also on Windows).
    path.unlink()


async def test_upload_timeout_is_actionable(
    tracker_client: TrackerClient, tmp_path: Path
) -> None:
    path = tmp_path / "report.txt"
    path.write_text("report")
    with aioresponses() as mock:
        mock.post(
            "https://api.tracker.yandex.net/v3/issues/TEST-123/attachments",
            exception=TimeoutError(),
        )
        with pytest.raises(TrackerAPITimeout):
            await tracker_client.issue_add_attachment("TEST-123", str(path))
    path.unlink()
