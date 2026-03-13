"""REST client for GitHub Issues API using PyGithub."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

from github import Auth, Github, RateLimitExceededException
from github.GithubObject import NotSet
from github.Issue import Issue
from github.Repository import Repository

from .models import Config, Task

MENTION_RE = re.compile(r"(?<![A-Za-z0-9-])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)")


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
            "repository": repo.full_name,
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

    def get_issue_with_activity(
        self,
        repo: Repository,
        issue_number: int,
    ) -> dict:
        """
        Get an issue with comments and timeline events (interactions).
        """
        issue_data = self.get_issue_with_comments(repo, issue_number)
        issue = repo.get_issue(issue_number)
        events = list(issue.get_events())

        issue_data["events"] = [
            {
                "event": e.event or "unknown",
                "actor": e.actor.login if e.actor else "unknown",
                "created_at": e.created_at,
                "assignee": e.assignee.login if getattr(e, "assignee", None) else None,
                "label": e.label.name if getattr(e, "label", None) else None,
                "milestone": e.milestone.title if getattr(e, "milestone", None) else None,
                "commit_id": getattr(e, "commit_id", None),
            }
            for e in events
        ]
        return issue_data

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

    def search_issues_by_mentions_or_assignment(
        self,
        username: str,
        org: Optional[str] = None,
        repo: Optional[str] = None,
        state: str = "all",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[Issue]:
        """
        Search issues where the user was mentioned or assigned.
        """
        base_parts = ["is:issue"]
        if repo:
            base_parts.append(f"repo:{repo}")
        elif org:
            base_parts.append(f"org:{org}")
        if state != "all":
            base_parts.append(f"is:{state}")
        if since:
            base_parts.append(f"updated:>={since.strftime('%Y-%m-%d')}")
        if until:
            base_parts.append(f"updated:<={until.strftime('%Y-%m-%d')}")

        query_mentions = " ".join(base_parts + [f"mentions:{username}"])
        query_assigned = " ".join(base_parts + [f"assignee:{username}"])

        try:
            mentioned = list(self.github.search_issues(query_mentions, sort="updated", order="desc"))
            assigned = list(self.github.search_issues(query_assigned, sort="updated", order="desc"))
        except RateLimitExceededException as e:
            raise RateLimitExceededException(
                status=e.status,
                data=e.data,
                headers=e.headers
            )

        seen = set()
        merged: List[Issue] = []
        for issue in mentioned + assigned:
            key = (issue.repository.full_name, issue.number)
            if key in seen:
                continue
            seen.add(key)
            merged.append(issue)

        return merged

    def search_issues_in_scope(
        self,
        org: Optional[str] = None,
        repo: Optional[str] = None,
        state: str = "all",
    ) -> List[Issue]:
        """List issues for a repository or organization scope."""
        if repo:
            owner, repo_name = repo.split("/", 1)
            repository = self.get_repo(owner, repo_name)
            return self.get_all_issues(repository, state=state)

        query_parts = ["is:issue"]
        if org:
            query_parts.append(f"org:{org}")
        if state != "all":
            query_parts.append(f"is:{state}")

        query = " ".join(query_parts)
        try:
            return list(self.github.search_issues(query, sort="updated", order="desc"))
        except RateLimitExceededException as e:
            raise RateLimitExceededException(
                status=e.status,
                data=e.data,
                headers=e.headers,
            )


def _to_utc_aware(dt: datetime) -> datetime:
    """Normalize datetime to UTC-aware for safe comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def extract_mentioned_users(text: str) -> set[str]:
    """Extract GitHub usernames referenced with @mention syntax."""
    if not text:
        return set()
    return {match.lower() for match in MENTION_RE.findall(text)}


def extract_referenced_users(issue_data: dict) -> dict[str, set[str]]:
    """Collect mentioned and assigned users from an issue payload."""
    mentioned_users = extract_mentioned_users(issue_data.get("body") or "")
    assigned_users = {assignee.lower() for assignee in issue_data.get("assignees", [])}

    for comment in issue_data.get("comments", []):
        mentioned_users.update(extract_mentioned_users(comment.get("body") or ""))

    for event in issue_data.get("events", []):
        assignee = event.get("assignee")
        if assignee:
            assigned_users.add(assignee.lower())

    return {
        "mentioned": mentioned_users,
        "assigned": assigned_users,
    }


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

    since_utc = _to_utc_aware(since) if since else None
    until_end_utc = None
    if until:
        until_end = datetime(until.year, until.month, until.day, 23, 59, 59, tzinfo=until.tzinfo)
        until_end_utc = _to_utc_aware(until_end)
    
    def in_range(dt: datetime) -> bool:
        """Check if a datetime falls within the range."""
        current = _to_utc_aware(dt)
        if since_utc and current < since_utc:
            return False
        if until_end_utc and current > until_end_utc:
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


def user_named_or_assigned_in_range(
    issue_data: dict,
    username: str,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> bool:
    """
    Check if user was mentioned or assigned within date range.
    """
    target = username.lower().lstrip("@")

    since_utc = _to_utc_aware(since) if since else None
    until_end_utc = None
    if until:
        until_end = datetime(until.year, until.month, until.day, 23, 59, 59, tzinfo=until.tzinfo)
        until_end_utc = _to_utc_aware(until_end)

    def in_range(dt: datetime) -> bool:
        current = _to_utc_aware(dt)
        if since_utc and current < since_utc:
            return False
        if until_end_utc and current > until_end_utc:
            return False
        return True

    # Issue body mention on creation date.
    body = (issue_data.get("body") or "").lower()
    if f"@{target}" in body and issue_data.get("created_at") and in_range(issue_data["created_at"]):
        return True

    # Comment mentions.
    for comment in issue_data.get("comments", []):
        comment_body = (comment.get("body") or "").lower()
        created_at = comment.get("created_at")
        if f"@{target}" in comment_body and created_at and in_range(created_at):
            return True

    # Assignment events.
    for event in issue_data.get("events", []):
        if event.get("event") not in ("assigned", "unassigned"):
            continue
        assignee = (event.get("assignee") or "").lower()
        created_at = event.get("created_at")
        if assignee == target and created_at and in_range(created_at):
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
