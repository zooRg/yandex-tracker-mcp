import pytest
from aioresponses import aioresponses

from mcp_tracker.tracker.custom.client import TrackerClient
from tests.aioresponses_utils import RequestCapture


@pytest.mark.parametrize("update", [False, True])
@pytest.mark.parametrize("attachment_ids", [None, [], ["42", "43"]])
async def test_comment_attachment_request_and_response(
    tracker_client: TrackerClient, update: bool, attachment_ids: list[str] | None
) -> None:
    capture = RequestCapture(
        payload={
            "id": 10,
            "text": "Keep this text",
        }
    )
    with aioresponses() as mock:
        if update:
            mock.patch(
                "https://api.tracker.yandex.net/v3/issues/TEST-123/comments/10",
                callback=capture.callback,
            )
            result = await tracker_client.issue_update_comment(
                "TEST-123", 10, text="Keep this text", attachment_ids=attachment_ids
            )
        else:
            mock.post(
                "https://api.tracker.yandex.net/v3/issues/TEST-123/comments",
                callback=capture.callback,
            )
            result = await tracker_client.issue_add_comment(
                "TEST-123", text="Keep this text", attachment_ids=attachment_ids
            )
    expected: dict[str, object] = {"text": "Keep this text"}
    if attachment_ids is not None:
        expected["attachmentIds"] = attachment_ids
    capture.last_request.assert_json_body(expected)
    assert result.text == "Keep this text"
