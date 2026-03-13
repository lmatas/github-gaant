"""Tests for monthly user issue export (mentioned/assigned)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from github_gaant.github_rest import (
    GitHubRESTClient,
    user_interacted_in_range,
    user_named_or_assigned_in_range,
)
from github_gaant.models import Config, DateFieldConfig
from github_gaant.sync import fetch_user_monthly_named_assigned_issues


def test_user_named_or_assigned_in_range_by_comment_mention():
    """User mention in comment inside range should match."""
    issue_data = {
        "body": "",
        "created_at": datetime(2026, 2, 1, 10, 0, 0),
        "comments": [
            {
                "body": "Ping @lmatas about this",
                "created_at": datetime(2026, 2, 5, 10, 0, 0),
            }
        ],
        "events": [],
    }
    since = datetime(2026, 2, 1)
    until = datetime(2026, 2, 28)
    assert user_named_or_assigned_in_range(issue_data, "lmatas", since, until) is True


def test_user_named_or_assigned_in_range_by_assignment_event():
    """Assignment event inside range should match."""
    issue_data = {
        "body": "",
        "created_at": datetime(2026, 1, 1, 10, 0, 0),
        "comments": [],
        "events": [
            {
                "event": "assigned",
                "assignee": "lmatas",
                "created_at": datetime(2026, 2, 10, 12, 0, 0),
            }
        ],
    }
    since = datetime(2026, 2, 1)
    until = datetime(2026, 2, 28)
    assert user_named_or_assigned_in_range(issue_data, "lmatas", since, until) is True


def test_user_named_or_assigned_in_range_handles_aware_datetimes():
    """Should not fail when issue timestamps are timezone-aware."""
    issue_data = {
        "body": "",
        "created_at": datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
        "comments": [
            {
                "body": "hola @lmatas",
                "created_at": datetime(2026, 2, 2, 10, 0, 0, tzinfo=timezone.utc),
            }
        ],
        "events": [],
    }
    since = datetime(2026, 2, 1)  # naive on purpose
    until = datetime(2026, 2, 28)  # naive on purpose
    assert user_named_or_assigned_in_range(issue_data, "lmatas", since, until) is True


def test_user_interacted_in_range_handles_aware_datetimes():
    """Legacy date-range filter should also handle aware timestamps."""
    issue_data = {
        "author": "lmatas",
        "created_at": datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc),
        "comments": [],
    }
    since = datetime(2026, 2, 1)  # naive on purpose
    until = datetime(2026, 2, 28)  # naive on purpose
    assert user_interacted_in_range(issue_data, "lmatas", since, until) is True


@patch("github_gaant.github_rest.Github")
def test_search_issues_by_mentions_or_assignment_deduplicates(mock_github_class):
    """Combined mentions/assignee search should deduplicate repeated issues."""
    mock_github = MagicMock()
    mock_github_class.return_value = mock_github

    issue_1 = MagicMock()
    issue_1.number = 1
    issue_1.repository.full_name = "myorg/repo-a"

    issue_2 = MagicMock()
    issue_2.number = 2
    issue_2.repository.full_name = "myorg/repo-a"

    # issue_1 appears in both queries and should be deduped.
    mock_github.search_issues.side_effect = [[issue_1], [issue_1, issue_2]]

    client = GitHubRESTClient("test_token")
    results = client.search_issues_by_mentions_or_assignment(
        username="lmatas",
        org="myorg",
        state="open",
        since=datetime(2026, 2, 1),
        until=datetime(2026, 2, 28),
    )

    assert len(results) == 2
    assert results[0] is issue_1
    assert results[1] is issue_2

    first_query = mock_github.search_issues.call_args_list[0][0][0]
    second_query = mock_github.search_issues.call_args_list[1][0][0]

    assert "mentions:lmatas" in first_query
    assert "assignee:lmatas" in second_query
    assert "org:myorg" in first_query
    assert "is:open" in first_query
    assert "updated:>=2026-02-01" in first_query
    assert "updated:<=2026-02-28" in first_query


@patch("github_gaant.github_rest.Github")
def test_search_issues_by_mentions_or_assignment_with_repo_scope(mock_github_class):
    """When repo is provided, query must use repo scope."""
    mock_github = MagicMock()
    mock_github_class.return_value = mock_github
    mock_github.search_issues.side_effect = [[], []]

    client = GitHubRESTClient("test_token")
    client.search_issues_by_mentions_or_assignment(
        username="lmatas",
        org="myorg",
        repo="myorg/repo-a",
    )

    query = mock_github.search_issues.call_args_list[0][0][0]
    assert "repo:myorg/repo-a" in query
    assert "org:myorg" not in query


@patch("github_gaant.sync.save_issue_thread")
@patch("github_gaant.sync.get_github_token")
def test_fetch_user_monthly_named_assigned_issues_exports_expected_folder(
    mock_get_token, mock_save_thread, tmp_path
):
    """Monthly export should create user-year-month folder and save matching issues."""
    mock_get_token.return_value = "test_token"

    issue_match = MagicMock()
    issue_match.number = 101
    issue_match.repository = MagicMock()

    issue_skip = MagicMock()
    issue_skip.number = 102
    issue_skip.repository = MagicMock()

    issue_101_data = {
        "number": 101,
        "repository": "myorg/repo-a",
        "title": "Issue 101",
        "body": "",
        "author": "other",
        "created_at": datetime(2026, 2, 2, 10, 0, 0),
        "updated_at": datetime(2026, 2, 2, 11, 0, 0),
        "state": "open",
        "labels": [],
        "assignees": [],
        "url": "https://github.com/myorg/repo-a/issues/101",
        "comments": [
            {
                "author": "other",
                "created_at": datetime(2026, 2, 3, 12, 0, 0),
                "updated_at": datetime(2026, 2, 3, 12, 0, 0),
                "body": "hi @lmatas",
            }
        ],
        "events": [],
    }
    issue_102_data = {
        "number": 102,
        "repository": "myorg/repo-b",
        "title": "Issue 102",
        "body": "",
        "author": "other",
        "created_at": datetime(2026, 2, 2, 10, 0, 0),
        "updated_at": datetime(2026, 2, 2, 11, 0, 0),
        "state": "open",
        "labels": [],
        "assignees": [],
        "url": "https://github.com/myorg/repo-b/issues/102",
        "comments": [],
        "events": [],
    }

    with patch.object(
        GitHubRESTClient,
        "search_issues_by_mentions_or_assignment",
        return_value=[issue_match, issue_skip],
    ):
        with patch.object(
            GitHubRESTClient,
            "get_issue_with_activity",
            side_effect=[issue_101_data, issue_102_data],
        ):
            total_found, total_included, total_excluded, path = (
                fetch_user_monthly_named_assigned_issues(
                    username="lmatas",
                    year=2026,
                    month=2,
                    org="myorg",
                    output_dir=tmp_path,
                )
            )

    assert total_found == 2
    assert total_included == 1
    assert total_excluded == 1
    assert path.name == "lmatas-2026-2-myorg"
    assert path.parent == tmp_path
    mock_save_thread.assert_called_once()
    assert mock_save_thread.call_args.kwargs["include_repo_in_name"] is True


@patch("github_gaant.sync.save_issue_thread")
@patch("github_gaant.sync.get_github_token")
def test_fetch_user_monthly_named_assigned_issues_passes_repo_filter(
    mock_get_token, mock_save_thread, tmp_path
):
    """Monthly fetch should pass repo filter to search."""
    mock_get_token.return_value = "test_token"
    issue = MagicMock()
    issue.number = 7
    issue.repository = MagicMock()

    issue_data = {
        "number": 7,
        "repository": "myorg/repo-a",
        "title": "Issue 7",
        "body": "@lmatas",
        "author": "other",
        "created_at": datetime(2026, 2, 2, 10, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 2, 2, 11, 0, 0, tzinfo=timezone.utc),
        "state": "open",
        "labels": [],
        "assignees": [],
        "url": "https://github.com/myorg/repo-a/issues/7",
        "comments": [],
        "events": [],
    }

    with patch.object(
        GitHubRESTClient,
        "search_issues_by_mentions_or_assignment",
        return_value=[issue],
    ) as mock_search:
        with patch.object(
            GitHubRESTClient,
            "get_issue_with_activity",
            return_value=issue_data,
        ):
            _, _, _, path = fetch_user_monthly_named_assigned_issues(
                username="lmatas",
                year=2026,
                month=2,
                repo="myorg/repo-a",
                output_dir=tmp_path,
            )

    assert mock_search.call_args.kwargs["repo"] == "myorg/repo-a"
    assert path.name == "lmatas-2026-2-myorg-repo-a"


@patch("github_gaant.cli.fetch_user_monthly_named_assigned_issues")
@patch("github_gaant.cli.load_config")
def test_fetch_user_monthly_cmd_explicit_org_ignores_default_repo(
    mock_load_config, mock_fetch_monthly
):
    """Explicit --org should ignore repo default from config."""
    from github_gaant.cli import fetch_user_monthly_cmd

    mock_load_config.return_value = Config(
        repo="LA-Referencia-IOI/a_planning_semantic",
        project_number=1,
        date_fields=DateFieldConfig(),
    )
    mock_fetch_monthly.return_value = (0, 0, 0, None)

    fetch_user_monthly_cmd(
        username="lmatas",
        year=2026,
        month=2,
        org="LA-Referencia-IOI",
        repo=None,
        config_path=None,
        output_dir=None,
        state="all",
        delay=0.0,
    )

    assert mock_fetch_monthly.call_args.kwargs["repo"] is None
    assert mock_fetch_monthly.call_args.kwargs["org"] == "LA-Referencia-IOI"
