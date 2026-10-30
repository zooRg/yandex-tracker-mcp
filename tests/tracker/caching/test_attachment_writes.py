from unittest.mock import AsyncMock

import pytest

from mcp_tracker.tracker.caching.client import make_cached_protocols
from mcp_tracker.tracker.proto.common import YandexAuth
from mcp_tracker.tracker.proto.issues import IssueProtocol
from mcp_tracker.tracker.proto.types.issues import IssueAttachment, IssueComment


async def test_upload_is_never_cached(yandex_auth: YandexAuth) -> None:
    original = AsyncMock(spec=IssueProtocol)
    original.issue_add_attachment.side_effect = [
        IssueAttachment.model_construct(id="1", name="report"),
        IssueAttachment.model_construct(id="2", name="report"),
    ]
    wrapped = make_cached_protocols({"ttl": 300}).issues(original)
    first = await wrapped.issue_add_attachment(
        "TEST-1", "/report", temporary=True, auth=yandex_auth
    )
    second = await wrapped.issue_add_attachment(
        "TEST-1", "/report", temporary=True, auth=yandex_auth
    )
    assert (first.id, second.id) == ("1", "2")
    assert original.issue_add_attachment.await_count == 2
    original.issue_add_attachment.assert_awaited_with(
        "TEST-1", "/report", temporary=True, auth=yandex_auth
    )


@pytest.mark.parametrize("update", [False, True])
async def test_comment_wrapper_keeps_attachment_ids(
    yandex_auth: YandexAuth, update: bool
) -> None:
    original = AsyncMock(spec=IssueProtocol)
    wrapped = make_cached_protocols({"ttl": 300}).issues(original)
    method = original.issue_update_comment if update else original.issue_add_comment
    method.return_value = IssueComment.model_construct(id=10, text="Report")
    if update:
        await wrapped.issue_update_comment(
            "TEST-1", 10, text="Report", attachment_ids=["42"], auth=yandex_auth
        )
    else:
        await wrapped.issue_add_comment(
            "TEST-1", text="Report", attachment_ids=["42"], auth=yandex_auth
        )
    assert method.call_args.kwargs["attachment_ids"] == ["42"]
    assert method.call_args.kwargs["auth"] == yandex_auth
