"""Pydantic models for GitHub Gaant."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator


class IssueState(str, Enum):
    """GitHub issue state."""
    OPEN = "open"
    CLOSED = "closed"


class TaskStatus(str, Enum):
    """Task status for Gantt visualization."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "active"
    DONE = "done"
    CRITICAL = "crit"


class Task(BaseModel):
    """Represents a GitHub issue as a Gantt task."""
    
    # GitHub identifiers
    issue_number: int
    issue_id: str  # GraphQL node ID
    project_item_id: Optional[str] = None  # ProjectV2Item ID
    
    # Basic info
    title: str
    body: Optional[str] = None
    state: IssueState = IssueState.OPEN
    url: Optional[str] = None
    
    # Gantt fields (from Project custom fields)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Assignments
    assignees: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    milestone: Optional[str] = None
    
    # Hierarchy (sub-issues)
    parent_issue_number: Optional[int] = None
    subtasks: List[Task] = Field(default_factory=list)
    
    @computed_field
    @property
    def progress(self) -> int:
        """Calculate progress as percentage of closed sub-issues."""
        if not self.subtasks:
            return 100 if self.state == IssueState.CLOSED else 0
        
        closed = sum(1 for t in self.subtasks if t.state == IssueState.CLOSED)
        return int((closed / len(self.subtasks)) * 100)
    
    @computed_field
    @property
    def status(self) -> TaskStatus:
        """Determine task status for Gantt visualization."""
        if self.state == IssueState.CLOSED:
            return TaskStatus.DONE
        if self.progress > 0:
            return TaskStatus.IN_PROGRESS
        return TaskStatus.NOT_STARTED
    
    @computed_field
    @property
    def duration_days(self) -> Optional[int]:
        """Calculate duration in days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return None


class Project(BaseModel):
    """Represents a GitHub Project V2."""
    
    id: str  # GraphQL node ID
    number: int
    title: str
    url: Optional[str] = None
    
    # Custom field IDs (resolved from field names)
    start_date_field_id: Optional[str] = None
    end_date_field_id: Optional[str] = None
    
    # All tasks in the project
    tasks: List[Task] = Field(default_factory=list)
    
    @computed_field
    @property
    def total_tasks(self) -> int:
        """Count all tasks including subtasks."""
        def count_recursive(tasks: List[Task]) -> int:
            total = len(tasks)
            for task in tasks:
                total += count_recursive(task.subtasks)
            return total
        return count_recursive(self.tasks)
    
    @computed_field
    @property
    def overall_progress(self) -> int:
        """Calculate overall project progress."""
        def collect_leaf_tasks(tasks: List[Task]) -> List[Task]:
            leaves = []
            for task in tasks:
                if task.subtasks:
                    leaves.extend(collect_leaf_tasks(task.subtasks))
                else:
                    leaves.append(task)
            return leaves
        
        leaves = collect_leaf_tasks(self.tasks)
        if not leaves:
            return 0
        closed = sum(1 for t in leaves if t.state == IssueState.CLOSED)
        return int((closed / len(leaves)) * 100)


class DateFieldConfig(BaseModel):
    """Configuration for date field mapping."""
    start: str = "Start Date"
    end: str = "Due Date"


class Config(BaseModel):
    """Application configuration."""
    
    repo: str  # format: "owner/repo"
    project_number: int
    date_fields: DateFieldConfig = Field(default_factory=DateFieldConfig)
    output_file: str = "gaant.yaml"
    labels_filter: List[str] = Field(default_factory=list)
    include_closed: bool = False
    
    @field_validator('repo', 'output_file', mode='before')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v
    
    @computed_field
    @property
    def owner(self) -> str:
        """Extract owner from repo string."""
        return self.repo.split("/")[0].strip()
    
    @computed_field
    @property
    def repo_name(self) -> str:
        """Extract repo name from repo string."""
        return self.repo.split("/")[1].strip()
