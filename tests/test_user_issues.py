"""Tests for user issues fetch functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from github_gaant.github_rest import user_interacted_in_range


class TestUserInteractedInRange:
    """Tests for user_interacted_in_range function."""
    
    def test_no_date_filter_always_true(self):
        """Without date filters, always returns True."""
        issue_data = {
            'author': 'testuser',
            'created_at': datetime(2025, 6, 15),
            'comments': [],
        }
        
        assert user_interacted_in_range(issue_data, 'testuser') is True
        assert user_interacted_in_range(issue_data, 'otheruser') is True
    
    def test_author_in_range(self):
        """User created issue within date range."""
        issue_data = {
            'author': 'testuser',
            'created_at': datetime(2025, 6, 15, 10, 30),
            'comments': [],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is True
    
    def test_author_before_range(self):
        """User created issue before date range."""
        issue_data = {
            'author': 'testuser',
            'created_at': datetime(2025, 5, 15),
            'comments': [],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is False
    
    def test_author_after_range(self):
        """User created issue after date range."""
        issue_data = {
            'author': 'testuser',
            'created_at': datetime(2025, 7, 15),
            'comments': [],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is False
    
    def test_comment_in_range(self):
        """User commented within date range."""
        issue_data = {
            'author': 'otheruser',
            'created_at': datetime(2025, 5, 15),
            'comments': [
                {
                    'author': 'testuser',
                    'created_at': datetime(2025, 6, 15),
                },
            ],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is True
    
    def test_comment_outside_range(self):
        """User commented but outside date range."""
        issue_data = {
            'author': 'otheruser',
            'created_at': datetime(2025, 5, 15),
            'comments': [
                {
                    'author': 'testuser',
                    'created_at': datetime(2025, 5, 20),
                },
            ],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is False
    
    def test_multiple_comments_one_in_range(self):
        """Multiple comments, at least one in range."""
        issue_data = {
            'author': 'otheruser',
            'created_at': datetime(2025, 5, 15),
            'comments': [
                {
                    'author': 'testuser',
                    'created_at': datetime(2025, 5, 20),
                },
                {
                    'author': 'testuser',
                    'created_at': datetime(2025, 6, 15),
                },
                {
                    'author': 'testuser',
                    'created_at': datetime(2025, 7, 10),
                },
            ],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is True
    
    def test_case_insensitive_username(self):
        """Username comparison is case-insensitive."""
        issue_data = {
            'author': 'TestUser',
            'created_at': datetime(2025, 6, 15),
            'comments': [],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is True
        assert user_interacted_in_range(issue_data, 'TESTUSER', since, until) is True
    
    def test_only_since_filter(self):
        """Only 'since' date provided."""
        issue_data = {
            'author': 'testuser',
            'created_at': datetime(2025, 6, 15),
            'comments': [],
        }
        
        since = datetime(2025, 6, 1)
        
        assert user_interacted_in_range(issue_data, 'testuser', since=since) is True
        
        # Before since
        issue_data['created_at'] = datetime(2025, 5, 15)
        assert user_interacted_in_range(issue_data, 'testuser', since=since) is False
    
    def test_only_until_filter(self):
        """Only 'until' date provided."""
        issue_data = {
            'author': 'testuser',
            'created_at': datetime(2025, 6, 15),
            'comments': [],
        }
        
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', until=until) is True
        
        # After until (including end of day)
        issue_data['created_at'] = datetime(2025, 7, 1, 0, 0, 1)
        assert user_interacted_in_range(issue_data, 'testuser', until=until) is False
    
    def test_until_includes_end_of_day(self):
        """'until' date includes the entire day (23:59:59)."""
        issue_data = {
            'author': 'testuser',
            'created_at': datetime(2025, 6, 30, 23, 59, 59),
            'comments': [],
        }
        
        until = datetime(2025, 6, 30)
        
        # Last second of the day should be included
        assert user_interacted_in_range(issue_data, 'testuser', until=until) is True
        
        # First second of next day should not
        issue_data['created_at'] = datetime(2025, 7, 1, 0, 0, 0)
        assert user_interacted_in_range(issue_data, 'testuser', until=until) is False
    
    def test_different_user_no_match(self):
        """Different user has no interaction."""
        issue_data = {
            'author': 'otheruser',
            'created_at': datetime(2025, 6, 15),
            'comments': [
                {
                    'author': 'anotheruser',
                    'created_at': datetime(2025, 6, 20),
                },
            ],
        }
        
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        assert user_interacted_in_range(issue_data, 'testuser', since, until) is False


class TestSearchIssuesByUser:
    """Tests for GitHubRESTClient.search_issues_by_user method."""
    
    @patch('github_gaant.github_rest.Github')
    def test_search_with_org(self, mock_github_class):
        """Search builds correct query with organization."""
        from github_gaant.github_rest import GitHubRESTClient
        
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.search_issues.return_value = []
        
        client = GitHubRESTClient("test_token")
        client.search_issues_by_user(username="testuser", org="testorg")
        
        # Verify the query contains expected parts
        call_args = mock_github.search_issues.call_args
        query = call_args[0][0]
        
        assert "org:testorg" in query
        assert "involves:testuser" in query
        assert "is:issue" in query
    
    @patch('github_gaant.github_rest.Github')
    def test_search_without_org(self, mock_github_class):
        """Search works without organization."""
        from github_gaant.github_rest import GitHubRESTClient
        
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.search_issues.return_value = []
        
        client = GitHubRESTClient("test_token")
        client.search_issues_by_user(username="testuser")
        
        call_args = mock_github.search_issues.call_args
        query = call_args[0][0]
        
        assert "org:" not in query
        assert "involves:testuser" in query
        assert "is:issue" in query
    
    @patch('github_gaant.github_rest.Github')
    def test_search_with_state_open(self, mock_github_class):
        """Search filters by open state."""
        from github_gaant.github_rest import GitHubRESTClient
        
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.search_issues.return_value = []
        
        client = GitHubRESTClient("test_token")
        client.search_issues_by_user(username="testuser", state="open")
        
        query = mock_github.search_issues.call_args[0][0]
        assert "is:open" in query
    
    @patch('github_gaant.github_rest.Github')
    def test_search_with_state_all(self, mock_github_class):
        """Search with 'all' state doesn't filter."""
        from github_gaant.github_rest import GitHubRESTClient
        
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.search_issues.return_value = []
        
        client = GitHubRESTClient("test_token")
        client.search_issues_by_user(username="testuser", state="all")
        
        query = mock_github.search_issues.call_args[0][0]
        assert "is:open" not in query
        assert "is:closed" not in query
    
    @patch('github_gaant.github_rest.Github')
    def test_search_with_since(self, mock_github_class):
        """Search includes updated filter when since is provided."""
        from github_gaant.github_rest import GitHubRESTClient
        
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.search_issues.return_value = []
        
        client = GitHubRESTClient("test_token")
        since = datetime(2025, 6, 1)
        client.search_issues_by_user(username="testuser", since=since)
        
        query = mock_github.search_issues.call_args[0][0]
        assert "updated:>=2025-06-01" in query
    
    @patch('github_gaant.github_rest.Github')
    def test_search_sort_order(self, mock_github_class):
        """Search uses correct sort order."""
        from github_gaant.github_rest import GitHubRESTClient
        
        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_github.search_issues.return_value = []
        
        client = GitHubRESTClient("test_token")
        client.search_issues_by_user(username="testuser")
        
        call_kwargs = mock_github.search_issues.call_args[1]
        assert call_kwargs['sort'] == "updated"
        assert call_kwargs['order'] == "desc"


class TestFetchUserIssuesIntegration:
    """Integration tests for fetch_user_issues function."""
    
    @patch('github_gaant.sync.save_issue_thread')
    @patch('github_gaant.sync.get_github_token')
    def test_fetch_user_issues_basic(self, mock_get_token, mock_save):
        """Fetch user issues basic flow."""
        from github_gaant.sync import fetch_user_issues
        from github_gaant.github_rest import GitHubRESTClient
        
        # Setup token mock
        mock_get_token.return_value = "test_token"
        
        # Mock the search and get methods directly
        mock_issue = MagicMock()
        mock_issue.number = 123
        mock_issue.repository = MagicMock()
        
        issue_data = {
            'number': 123,
            'title': 'Test Issue',
            'body': 'Test body',
            'author': 'testuser',
            'created_at': datetime(2025, 6, 15),
            'updated_at': datetime(2025, 6, 16),
            'state': 'open',
            'labels': [],
            'assignees': [],
            'url': 'https://github.com/org/repo/issues/123',
            'comments': [],
        }
        
        with patch.object(GitHubRESTClient, 'search_issues_by_user', return_value=[mock_issue]):
            with patch.object(GitHubRESTClient, 'get_issue_with_comments', return_value=issue_data):
                # Run function
                total_found, total_included, total_excluded, path = fetch_user_issues(
                    username="testuser",
                    org="testorg",
                )
        
        # Verify results
        assert total_found == 1
        assert total_included == 1
        assert total_excluded == 0
        assert path is not None
        assert path.name == "testuser"
        
        # Verify save was called
        mock_save.assert_called_once()
    
    @patch('github_gaant.sync.save_issue_thread')
    @patch('github_gaant.sync.get_github_token')
    def test_fetch_user_issues_with_date_filter(self, mock_get_token, mock_save):
        """Fetch user issues with date filtering."""
        from github_gaant.sync import fetch_user_issues
        from github_gaant.github_rest import GitHubRESTClient
        
        # Setup token mock
        mock_get_token.return_value = "test_token"
        
        # Mock issue search - 2 issues
        mock_issue1 = MagicMock()
        mock_issue1.number = 123
        mock_issue1.repository = MagicMock()
        
        mock_issue2 = MagicMock()
        mock_issue2.number = 124
        mock_issue2.repository = MagicMock()
        
        # First issue: user commented in range
        issue1_data = {
            'number': 123,
            'title': 'Test Issue 1',
            'body': 'Test',
            'author': 'otheruser',
            'created_at': datetime(2025, 5, 15),
            'updated_at': datetime(2025, 6, 16),
            'state': 'open',
            'labels': [],
            'assignees': [],
            'url': 'https://github.com/org/repo/issues/123',
            'comments': [
                {
                    'author': 'testuser',
                    'created_at': datetime(2025, 6, 15),
                    'body': 'Comment',
                },
            ],
        }
        
        # Second issue: user created before range
        issue2_data = {
            'number': 124,
            'title': 'Test Issue 2',
            'body': 'Test',
            'author': 'testuser',
            'created_at': datetime(2025, 5, 15),
            'updated_at': datetime(2025, 6, 16),
            'state': 'open',
            'labels': [],
            'assignees': [],
            'url': 'https://github.com/org/repo/issues/124',
            'comments': [],
        }
        
        # Run function with date filter
        since = datetime(2025, 6, 1)
        until = datetime(2025, 6, 30)
        
        with patch.object(GitHubRESTClient, 'search_issues_by_user', return_value=[mock_issue1, mock_issue2]):
            with patch.object(GitHubRESTClient, 'get_issue_with_comments', side_effect=[issue1_data, issue2_data]):
                total_found, total_included, total_excluded, path = fetch_user_issues(
                    username="testuser",
                    org="testorg",
                    since=since,
                    until=until,
                )
        
        # Verify results
        assert total_found == 2
        assert total_included == 1  # Only issue 123
        assert total_excluded == 1  # Issue 124 excluded
        
        # Verify only one issue was saved
        assert mock_save.call_count == 1
        saved_issue = mock_save.call_args[0][0]
        assert saved_issue['number'] == 123
    
    @patch('github_gaant.sync.get_github_token')
    def test_fetch_user_issues_no_results(self, mock_get_token):
        """Fetch user issues with no results."""
        from github_gaant.sync import fetch_user_issues
        from github_gaant.github_rest import GitHubRESTClient
        
        # Setup token mock
        mock_get_token.return_value = "test_token"
        
        # No issues found
        with patch.object(GitHubRESTClient, 'search_issues_by_user', return_value=[]):
            # Run function
            total_found, total_included, total_excluded, path = fetch_user_issues(
                username="testuser",
                org="testorg",
            )
        
        # Verify results
        assert total_found == 0
        assert total_included == 0
        assert total_excluded == 0
        assert path is None


class TestFetchUserIssuesWithExcludeStatus:
    """Tests for fetch_user_issues with exclude_status filtering."""
    
    @patch('github_gaant.sync.save_issue_thread')
    @patch('github_gaant.sync.get_github_token')
    def test_exclude_by_project_status(self, mock_get_token, mock_save):
        """Issues with excluded project status are filtered out."""
        from github_gaant.sync import fetch_user_issues
        from github_gaant.github_rest import GitHubRESTClient
        from github_gaant.github_graphql import GitHubGraphQLClient
        
        # Setup token mock
        mock_get_token.return_value = "test_token"
        
        # Mock issue search - 3 issues
        mock_issue1 = MagicMock()
        mock_issue1.number = 1
        mock_issue1.repository = MagicMock()
        
        mock_issue2 = MagicMock()
        mock_issue2.number = 2
        mock_issue2.repository = MagicMock()
        
        mock_issue3 = MagicMock()
        mock_issue3.number = 3
        mock_issue3.repository = MagicMock()
        
        # Mock project data
        mock_project_data = {
            "id": "PVT_project1",
            "number": 1,
            "title": "Test Project",
        }
        
        # Mock project items with status field values
        mock_project_items = [
            {
                "id": "PVTI_1",
                "content": {"number": 1},
                "fieldValues": {
                    "nodes": [{
                        "name": "Todo",
                        "field": {"name": "Status"}
                    }]
                }
            },
            {
                "id": "PVTI_2",
                "content": {"number": 2},
                "fieldValues": {
                    "nodes": [{
                        "name": "In Progress",
                        "field": {"name": "Status"}
                    }]
                }
            },
            {
                "id": "PVTI_3",
                "content": {"number": 3},
                "fieldValues": {
                    "nodes": []  # No status
                }
            },
        ]
        
        # Issue data
        issue1_data = {
            'number': 1, 'title': 'Issue with Todo status', 'body': 'Test',
            'author': 'testuser', 'created_at': datetime(2025, 6, 15),
            'updated_at': datetime(2025, 6, 16), 'state': 'open',
            'labels': [], 'assignees': [],
            'url': 'https://github.com/org/repo/issues/1', 'comments': [],
        }
        
        issue2_data = {
            'number': 2, 'title': 'Issue in progress', 'body': 'Test',
            'author': 'testuser', 'created_at': datetime(2025, 6, 15),
            'updated_at': datetime(2025, 6, 16), 'state': 'open',
            'labels': [], 'assignees': [],
            'url': 'https://github.com/org/repo/issues/2', 'comments': [],
        }
        
        issue3_data = {
            'number': 3, 'title': 'Issue without status', 'body': 'Test',
            'author': 'testuser', 'created_at': datetime(2025, 6, 15),
            'updated_at': datetime(2025, 6, 16), 'state': 'open',
            'labels': [], 'assignees': [],
            'url': 'https://github.com/org/repo/issues/3', 'comments': [],
        }
        
        with patch.object(GitHubRESTClient, 'search_issues_by_user', return_value=[mock_issue1, mock_issue2, mock_issue3]):
            with patch.object(GitHubRESTClient, 'get_issue_with_comments', side_effect=[issue1_data, issue2_data, issue3_data]):
                with patch.object(GitHubGraphQLClient, 'get_project', return_value=mock_project_data):
                    with patch.object(GitHubGraphQLClient, 'get_project_items_with_issues', return_value=mock_project_items):
                        # Run with exclude_status
                        total_found, total_included, total_excluded, path = fetch_user_issues(
                            username="testuser",
                            org="testorg",
                            exclude_status=["Todo"],
                            project_number=1,
                            status_field="Status",
                        )
        
        # Verify results - Issue 1 excluded (Todo status), 2 and 3 included
        assert total_found == 3
        assert total_included == 2
        assert total_excluded == 1
        
        # Verify save was called twice (issues 2 and 3)
        assert mock_save.call_count == 2
    
    @patch('github_gaant.sync.save_issue_thread')
    @patch('github_gaant.sync.get_github_token')
    def test_exclude_multiple_statuses(self, mock_get_token, mock_save):
        """Multiple status values can be excluded."""
        from github_gaant.sync import fetch_user_issues
        from github_gaant.github_rest import GitHubRESTClient
        from github_gaant.github_graphql import GitHubGraphQLClient
        
        mock_get_token.return_value = "test_token"
        
        mock_issue1 = MagicMock()
        mock_issue1.number = 1
        mock_issue1.repository = MagicMock()
        
        mock_issue2 = MagicMock()
        mock_issue2.number = 2
        mock_issue2.repository = MagicMock()
        
        mock_project_data = {"id": "PVT_1", "number": 1, "title": "Test"}
        
        mock_project_items = [
            {
                "id": "PVTI_1",
                "content": {"number": 1},
                "fieldValues": {"nodes": [{"name": "Todo", "field": {"name": "Status"}}]}
            },
            {
                "id": "PVTI_2",
                "content": {"number": 2},
                "fieldValues": {"nodes": [{"name": "Backlog", "field": {"name": "Status"}}]}
            },
        ]
        
        issue1_data = {
            'number': 1, 'title': 'Todo issue', 'body': 'Test',
            'author': 'testuser', 'created_at': datetime(2025, 6, 15),
            'updated_at': datetime(2025, 6, 16), 'state': 'open',
            'labels': [], 'assignees': [],
            'url': 'https://github.com/org/repo/issues/1', 'comments': [],
        }
        
        issue2_data = {
            'number': 2, 'title': 'Backlog issue', 'body': 'Test',
            'author': 'testuser', 'created_at': datetime(2025, 6, 15),
            'updated_at': datetime(2025, 6, 16), 'state': 'open',
            'labels': [], 'assignees': [],
            'url': 'https://github.com/org/repo/issues/2', 'comments': [],
        }
        
        with patch.object(GitHubRESTClient, 'search_issues_by_user', return_value=[mock_issue1, mock_issue2]):
            with patch.object(GitHubRESTClient, 'get_issue_with_comments', side_effect=[issue1_data, issue2_data]):
                with patch.object(GitHubGraphQLClient, 'get_project', return_value=mock_project_data):
                    with patch.object(GitHubGraphQLClient, 'get_project_items_with_issues', return_value=mock_project_items):
                        total_found, total_included, total_excluded, path = fetch_user_issues(
                            username="testuser",
                            org="testorg",
                            exclude_status=["Todo", "Backlog"],
                            project_number=1,
                        )
        
        # Both issues should be excluded
        assert total_found == 2
        assert total_included == 0
        assert total_excluded == 2
        assert mock_save.call_count == 0

