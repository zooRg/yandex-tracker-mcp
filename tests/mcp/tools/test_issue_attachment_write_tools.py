from unittest.mock import AsyncMock

import pytest
from mcp.client.session import ClientSession

from mcp_tracker.mcp.context import AppContext
from mcp_tracker.mcp.server import create_mcp_server
from mcp_tracker.settings import Settings
from mcp_tracker.tracker.proto.common import YandexAuth
from mcp_tracker.tracker.proto.types.issues import IssueAttachment, IssueComment
from tests.mcp.conftest import (
    get_tool_result_content,
    make_test_lifespan,
    safe_client_session,
)


@pytest.mark.parametrize("temporary", [False, True])
async def test_upload_returns_metadata(
    client_session: ClientSession, mock_issues_protocol: AsyncMock, temporary: bool
) -> None:
    mock_issues_protocol.issue_add_attachment.return_value = (
        IssueAttachment.model_construct(
            id="42", name="report.md", comment_id="comment-long-id"
        )
    )
    result = await client_session.call_tool(
        "issue_add_attachment",
        {
            "issue_id": "TEST-123",
            "file_path": "/reports/report.md",
            "temporary": temporary,
        },
    )
    assert not result.isError
    assert get_tool_result_content(result)["id"] == "42"
    assert get_tool_result_content(result)["commentId"] == "comment-long-id"
    mock_issues_protocol.issue_add_attachment.assert_awaited_once_with(
        "TEST-123", "/reports/report.md", temporary=temporary, auth=YandexAuth()
    )


@pytest.mark.parametrize("transport", ["sse", "streamable-http"])
async def test_remote_clients_cannot_read_server_files(
    test_settings: Settings,
    mock_app_context: AppContext,
    mock_issues_protocol: AsyncMock,
    transport: str,
) -> None:
    settings = test_settings.model_copy(update={"transport": transport})
    server = create_mcp_server(
        settings=settings, lifespan=make_test_lifespan(mock_app_context)
    )
    async with safe_client_session(server) as session:
        result = await session.call_tool(
            "issue_add_attachment", {"issue_id": "TEST-123", "file_path": "/secret"}
        )
    assert result.isError
    assert "stdio" in str(result.content)
    mock_issues_protocol.issue_add_attachment.assert_not_awaited()


async def test_restricted_queue_rejected_before_file_access(
    client_session_with_limits: ClientSession, mock_issues_protocol: AsyncMock
) -> None:
    result = await client_session_with_limits.call_tool(
        "issue_add_attachment",
        {
            "issue_id": "RESTRICTED-1",
            "file_path": "/secret",
            "temporary": True,
        },
    )
    assert result.isError
    mock_issues_protocol.issue_add_attachment.assert_not_awaited()


async def test_read_only_queue_rejected_before_file_access(
    client_session_with_read_only_queues: ClientSession, mock_issues_protocol: AsyncMock
) -> None:
    result = await client_session_with_read_only_queues.call_tool(
        "issue_add_attachment",
        {
            "issue_id": "READONLY-1",
            "file_path": "/secret",
        },
    )
    assert result.isError
    mock_issues_protocol.issue_add_attachment.assert_not_awaited()


@pytest.mark.parametrize("tool_name", ["issue_add_comment", "issue_update_comment"])
async def test_comment_attachment_ids_and_result(
    client_session: ClientSession, mock_issues_protocol: AsyncMock, tool_name: str
) -> None:
    method = getattr(mock_issues_protocol, tool_name)
    method.return_value = IssueComment.model_construct(
        id=10,
        text="Report",
    )
    arguments: dict[str, object] = {
        "issue_id": "TEST-123",
        "text": "Report",
        "attachment_ids": ["42"],
    }
    if tool_name == "issue_update_comment":
        arguments["comment_id"] = 10
    result = await client_session.call_tool(tool_name, arguments)
    assert not result.isError
    assert method.call_args.kwargs["attachment_ids"] == ["42"]
    assert get_tool_result_content(result)["text"] == "Report"
