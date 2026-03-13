"""Tests for referenced user discovery."""

from unittest.mock import MagicMock, patch

from github_gaant.github_rest import (
    GitHubRESTClient,
    extract_mentioned_users,
    extract_referenced_users,
)
from github_gaant.models import Config, DateFieldConfig
from github_gaant.sync import collect_referenced_users


def test_extract_mentioned_users_finds_unique_logins():
    """Mention parser should normalize and deduplicate usernames."""
    text = "Ping @Lmatas and @other-user. Repeating @lmatas should dedupe."
    assert extract_mentioned_users(text) == {"lmatas", "other-user"}


def test_extract_referenced_users_combines_mentions_and_assignments():
    """Issue payload should return distinct mentioned and assigned users."""
    issue_data = {
        "body": "Owner is @lmatas",
        "assignees": ["reviewer1"],
        "comments": [
            {"body": "Also ask @reviewer2 and @lmatas"},
        ],
        "events": [
            {"assignee": "reviewer3"},
        ],
    }

    referenced = extract_referenced_users(issue_data)

    assert referenced["mentioned"] == {"lmatas", "reviewer2"}
    assert referenced["assigned"] == {"reviewer1", "reviewer3"}


@patch("github_gaant.github_rest.Github")
def test_search_issues_in_scope_uses_org_query(mock_github_class):
    """Organization scope should query GitHub search."""
    mock_github = MagicMock()
    mock_github_class.return_value = mock_github
    mock_github.search_issues.return_value = []

    client = GitHubRESTClient("token")
    client.search_issues_in_scope(org="myorg", state="open")

    query = mock_github.search_issues.call_args[0][0]
    assert "org:myorg" in query
    assert "is:open" in query


@patch("github_gaant.sync.get_github_token")
def test_collect_referenced_users_aggregates_across_issues(mock_get_token):
    """Aggregate per-user counts across mention and assignment sources."""
    mock_get_token.return_value = "token"

    issue_1 = MagicMock()
    issue_1.number = 1
    issue_1.repository = MagicMock()

    issue_2 = MagicMock()
    issue_2.number = 2
    issue_2.repository = MagicMock()

    issue_data_1 = {
        "body": "Hi @alice",
        "assignees": ["bob"],
        "comments": [{"body": "cc @charlie"}],
        "events": [],
    }
    issue_data_2 = {
        "body": "Hi @alice",
        "assignees": ["alice"],
        "comments": [],
        "events": [{"assignee": "bob"}],
    }

    with patch.object(
        GitHubRESTClient,
        "search_issues_in_scope",
        return_value=[issue_1, issue_2],
    ):
        with patch.object(
            GitHubRESTClient,
            "get_issue_with_activity",
            side_effect=[issue_data_1, issue_data_2],
        ):
            total_issues, summaries = collect_referenced_users(repo="myorg/repo-a")

    assert total_issues == 2
    summary_map = {item.username: item for item in summaries}
    assert summary_map["alice"].issues == 2
    assert summary_map["alice"].mentioned_in == 2
    assert summary_map["alice"].assigned_in == 1
    assert summary_map["bob"].issues == 2
    assert summary_map["bob"].assigned_in == 2
    assert summary_map["charlie"].issues == 1
    assert summary_map["charlie"].mentioned_in == 1


@patch("github_gaant.cli.collect_referenced_users")
@patch("github_gaant.cli.load_config")
def test_list_referenced_users_cmd_explicit_org_ignores_default_repo(
    mock_load_config, mock_collect
):
    """Explicit org should ignore repo default from config."""
    from github_gaant.cli import list_referenced_users_cmd
    from github_gaant.sync import ReferencedUserSummary

    mock_load_config.return_value = Config(
        repo="LA-Referencia-IOI/a_planning_semantic",
        project_number=1,
        date_fields=DateFieldConfig(),
    )
    mock_collect.return_value = (1, [ReferencedUserSummary(username="lmatas", issues=1)])

    list_referenced_users_cmd(
        org="LA-Referencia-IOI",
        repo=None,
        config_path=None,
        state="all",
        delay=0.0,
    )

    assert mock_collect.call_args.kwargs["repo"] is None
    assert mock_collect.call_args.kwargs["org"] == "LA-Referencia-IOI"
