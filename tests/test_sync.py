"""Tests for synchronization helpers."""

from pathlib import Path

from github_gaant.models import Task
from github_gaant.sync import compare_tasks, load_issue_body


def test_compare_tasks_ignores_remote_body_when_local_body_is_missing():
    """Body is not considered changed when local body is not explicitly provided."""
    local = Task(issue_number=1, issue_id="I_1", title="Task", body=None)
    remote = Task(issue_number=1, issue_id="I_1", title="Task", body="Remote body")

    changes = compare_tasks(local, remote)

    assert "body: content changed" not in changes


def test_compare_tasks_detects_body_change_when_local_body_is_explicit():
    """Body changes are detected when local body is explicitly set."""
    local = Task(issue_number=1, issue_id="I_1", title="Task", body="")
    remote = Task(issue_number=1, issue_id="I_1", title="Task", body="Remote body")

    changes = compare_tasks(local, remote)

    assert "body: content changed" in changes


def test_load_issue_body_returns_empty_string_when_file_is_cleared(tmp_path: Path):
    """A body file with only whitespace means explicit body clearing."""
    body_file = tmp_path / "12.md"
    body_file.write_text("<!-- Issue #12: Title -->\n\n   \n", encoding="utf-8")

    loaded = load_issue_body(12, tmp_path)

    assert loaded == ""
