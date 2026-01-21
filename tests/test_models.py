"""Tests for models."""

from datetime import date

import pytest

from src.models import IssueState, Project, Task, TaskStatus


class TestTask:
    """Tests for Task model."""
    
    def test_progress_no_subtasks_open(self):
        """Open task without subtasks has 0% progress."""
        task = Task(
            issue_number=1,
            issue_id="I_1",
            title="Test",
            state=IssueState.OPEN,
        )
        assert task.progress == 0
    
    def test_progress_no_subtasks_closed(self):
        """Closed task without subtasks has 100% progress."""
        task = Task(
            issue_number=1,
            issue_id="I_1",
            title="Test",
            state=IssueState.CLOSED,
        )
        assert task.progress == 100
    
    def test_progress_with_subtasks(self):
        """Progress is calculated from subtasks."""
        task = Task(
            issue_number=1,
            issue_id="I_1",
            title="Parent",
            subtasks=[
                Task(issue_number=2, issue_id="I_2", title="Sub 1", state=IssueState.CLOSED),
                Task(issue_number=3, issue_id="I_3", title="Sub 2", state=IssueState.OPEN),
            ],
        )
        assert task.progress == 50
    
    def test_status_done(self):
        """Closed task has DONE status."""
        task = Task(
            issue_number=1,
            issue_id="I_1",
            title="Test",
            state=IssueState.CLOSED,
        )
        assert task.status == TaskStatus.DONE
    
    def test_status_in_progress(self):
        """Task with partial progress is IN_PROGRESS."""
        task = Task(
            issue_number=1,
            issue_id="I_1",
            title="Parent",
            subtasks=[
                Task(issue_number=2, issue_id="I_2", title="Sub 1", state=IssueState.CLOSED),
                Task(issue_number=3, issue_id="I_3", title="Sub 2", state=IssueState.OPEN),
            ],
        )
        assert task.status == TaskStatus.IN_PROGRESS
    
    def test_duration_days(self):
        """Duration is calculated from dates."""
        task = Task(
            issue_number=1,
            issue_id="I_1",
            title="Test",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 25),
        )
        assert task.duration_days == 6  # Inclusive


class TestProject:
    """Tests for Project model."""
    
    def test_total_tasks(self):
        """Total tasks includes subtasks."""
        project = Project(
            id="P_1",
            number=1,
            title="Test Project",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Parent",
                    subtasks=[
                        Task(issue_number=2, issue_id="I_2", title="Sub 1"),
                        Task(issue_number=3, issue_id="I_3", title="Sub 2"),
                    ],
                ),
                Task(issue_number=4, issue_id="I_4", title="Single"),
            ],
        )
        assert project.total_tasks == 4
    
    def test_overall_progress(self):
        """Overall progress is based on leaf tasks."""
        project = Project(
            id="P_1",
            number=1,
            title="Test Project",
            tasks=[
                Task(
                    issue_number=1,
                    issue_id="I_1",
                    title="Parent",
                    subtasks=[
                        Task(issue_number=2, issue_id="I_2", title="Sub 1", state=IssueState.CLOSED),
                        Task(issue_number=3, issue_id="I_3", title="Sub 2", state=IssueState.OPEN),
                    ],
                ),
            ],
        )
        assert project.overall_progress == 50
