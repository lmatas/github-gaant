"""REST client for GitHub Issues API using PyGithub."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from github import Auth, Github, RateLimitExceededException
from github.GithubObject import NotSet
from github.Issue import Issue
from github.Repository import Repository

from .models import Config, Task


class GitHubRESTClient:
    """Client for GitHub REST API (Issues operations)."""
    
    def __init__(self, token: str):
        """Initialize the REST client."""
        auth = Auth.Token(token)
        self.github = Github(auth=auth)
    
    def get_repo(self, owner: str, repo_name: str) -> Repository:
        """Get a repository object."""
        return self.github.get_repo(f"{owner}/{repo_name}")
    
    def get_issue(self, repo: Repository, issue_number: int) -> Issue:
        """Get a single issue."""
        return repo.get_issue(issue_number)
    
    def create_issue(
        self,
        repo: Repository,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone_title: Optional[str] = None,
    ) -> Issue:
        """Create a new issue."""
        # Find milestone by title if provided
        milestone = None
        if milestone_title:
            for m in repo.get_milestones(state="open"):
                if m.title == milestone_title:
                    milestone = m
                    break
        
        return repo.create_issue(
            title=title,
            body=body or "",
            labels=labels or [],
            assignees=assignees or [],
            milestone=milestone or NotSet,
        )
    
    def update_issue(
        self,
        issue: Issue,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Issue:
        """Update an existing issue."""
        kwargs = {}
        
        if title is not None:
            kwargs["title"] = title
        if body is not None:
            kwargs["body"] = body
        if state is not None:
            kwargs["state"] = state
        if labels is not None:
            kwargs["labels"] = labels
        if assignees is not None:
            kwargs["assignees"] = assignees
        
        if kwargs:
            issue.edit(**kwargs)
        
        return issue
    
    def close_issue(self, issue: Issue) -> Issue:
        """Close an issue."""
        issue.edit(state="closed")
        return issue
    
    def reopen_issue(self, issue: Issue) -> Issue:
        """Reopen a closed issue."""
        issue.edit(state="open")
        return issue
    
    def get_all_issues(
        self, 
        repo: Repository, 
        state: str = "open",
        labels: Optional[List[str]] = None,
    ) -> List[Issue]:
        """Get all issues from a repository."""
        kwargs = {"state": state}
        if labels:
            kwargs["labels"] = labels
        
        return list(repo.get_issues(**kwargs))
    
    def add_sub_issue(
        self,
        repo: Repository,
        parent_issue_number: int,
        child_issue_number: int,
    ) -> bool:
        """
        Add a sub-issue relationship.
        Note: This uses the GitHub API for sub-issues which may require 
        specific permissions or be in beta.
        """
        # The sub-issues API is accessed via GraphQL primarily
        # For REST, we'd need to use the specific endpoint
        # This is a placeholder - actual implementation would use GraphQL
        return False
    
    def get_issue_node_id(self, issue: Issue) -> str:
        """Get the GraphQL node ID for an issue."""
        return issue.raw_data.get("node_id", "")
    
    def get_issue_with_comments(
        self,
        repo: Repository,
        issue_number: int,
    ) -> dict:
        """
        Get an issue with all its comments.
        
        Returns a dict with issue data and comments list.
        """
        issue = repo.get_issue(issue_number)
        comments = list(issue.get_comments())
        
        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "state": issue.state,
            "author": issue.user.login if issue.user else "unknown",
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
            "labels": [label.name for label in issue.labels],
            "assignees": [a.login for a in issue.assignees],
            "url": issue.html_url,
            "comments": [
                {
                    "author": c.user.login if c.user else "unknown",
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "body": c.body or "",
                }
                for c in comments
            ],
        }

    def search_issues_by_user(
        self,
        username: str,
        org: Optional[str] = None,
        state: str = "all",
        since: Optional[datetime] = None,
    ) -> List[Issue]:
        """
        Search for issues where a user has interacted in an organization.
        
        Args:
            username: GitHub username to search for
            org: Organization name (optional)
            state: Issue state filter (open/closed/all)
            since: Only include issues updated after this date (optimization)
        
        Returns:
            List of Issue objects matching the search criteria
        
        Raises:
            RateLimitExceededException: If GitHub API rate limit is exceeded
        """
        query_parts = []
        
        if org:
            query_parts.append(f"org:{org}")
        
        query_parts.append(f"involves:{username}")
        query_parts.append("is:issue")  # Exclude PRs
        
        if state != "all":
            query_parts.append(f"is:{state}")
        
        # Pre-filter by updated date for optimization
        if since:
            query_parts.append(f"updated:>={since.strftime('%Y-%m-%d')}")
        
        query = " ".join(query_parts)
        
        try:
            # PyGithub handles pagination automatically
            return list(self.github.search_issues(query, sort="updated", order="desc"))
        except RateLimitExceededException as e:
            # Re-raise with more context
            raise RateLimitExceededException(
                status=e.status,
                data=e.data,
                headers=e.headers
            )


def user_interacted_in_range(
    issue_data: dict,
    username: str,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> bool:
    """
    Check if a user has interacted with an issue within a date range.
    
    Interaction is defined as:
    - Creating the issue (author)
    - Adding a comment
    
    Args:
        issue_data: Dictionary from get_issue_with_comments()
        username: GitHub username to check
        since: Start of date range (inclusive)
        until: End of date range (inclusive, end of day)
    
    Returns:
        True if user has at least one interaction in the date range
    """
    # If no date filters, always return True
    if since is None and until is None:
        return True
    
    def in_range(dt: datetime) -> bool:
        """Check if a datetime falls within the range."""
        if since and dt < since:
            return False
        if until:
            # Include the entire "until" day (up to 23:59:59)
            until_end = datetime(until.year, until.month, until.day, 23, 59, 59)
            if dt > until_end:
                return False
        return True
    
    # Check if user created the issue within the range
    if issue_data['author'].lower() == username.lower():
        if in_range(issue_data['created_at']):
            return True
    
    # Check if user commented within the range
    for comment in issue_data['comments']:
        if comment['author'].lower() == username.lower():
            if in_range(comment['created_at']):
                return True
    
    return False


def create_issue_from_task(
    client: GitHubRESTClient,
    repo: Repository,
    task: Task,
) -> Issue:
    """Create a GitHub issue from a Task model."""
    return client.create_issue(
        repo=repo,
        title=task.title,
        body=task.body,
        labels=task.labels,
        assignees=task.assignees,
        milestone_title=task.milestone,
    )


def update_issue_from_task(
    client: GitHubRESTClient,
    issue: Issue,
    task: Task,
) -> Issue:
    """Update a GitHub issue from a Task model."""
    return client.update_issue(
        issue=issue,
        title=task.title,
        body=task.body,
        labels=task.labels,
        assignees=task.assignees,
    )
