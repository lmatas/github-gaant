"""REST client for GitHub Issues API using PyGithub."""

from __future__ import annotations

from typing import List, Optional

from github import Auth, Github
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
