"""Data models for Canvas API responses."""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Course:
    """Course from GET /users/self/courses."""
    id: int
    name: str
    raw: dict  # full JSON for any extra fields


@dataclass
class Announcement:
    """Announcement from GET /announcements."""
    id: int
    title: str
    message: str
    context_code: str  # e.g. course_123456
    html_url: str
    created_at: str
    raw: dict


@dataclass
class Assignment:
    """Assignment from GET /courses/:id/assignments."""
    id: int
    name: str
    course_id: int
    due_at: Optional[str]
    html_url: str
    raw: dict


@dataclass
class PlannerItem:
    """Item from GET /planner/items (assignment, quiz, etc.)."""
    plannable_id: int
    plannable_type: str  # assignment, quiz, discussion_topic, etc.
    course_id: int
    html_url: str
    due_at: Optional[str]
    title: str  # from plannable
    raw: dict


def course_from_dict(d: dict) -> Course:
    return Course(
        id=d["id"],
        name=d.get("name", ""),
        raw=d,
    )


def announcement_from_dict(d: dict) -> Announcement:
    return Announcement(
        id=d["id"],
        title=d.get("title", ""),
        message=d.get("message", ""),
        context_code=d.get("context_code", ""),
        html_url=d.get("url", "") or _announcement_url(d),
        created_at=d.get("created_at", ""),
        raw=d,
    )


def _announcement_url(d: dict) -> str:
    # context_code is e.g. course_123456
    base = "https://canvas.instructure.com"
    ctx = d.get("context_code", "")
    if ctx.startswith("course_"):
        cid = ctx.replace("course_", "")
        return f"{base}/courses/{cid}/discussion_topics/{d['id']}"
    return base


def assignment_from_dict(d: dict) -> Assignment:
    return Assignment(
        id=d["id"],
        name=d.get("name", ""),
        course_id=d.get("course_id", 0),
        due_at=d.get("due_at"),
        html_url=d.get("html_url", ""),
        raw=d,
    )


def planner_item_from_dict(d: dict) -> PlannerItem:
    plannable = d.get("plannable") or {}
    due = plannable.get("due_at") or d.get("due_at")
    title = plannable.get("title") or plannable.get("name") or str(d.get("plannable_id", ""))
    base = "https://canvas.instructure.com"
    url = d.get("html_url", "")
    if url and not url.startswith("http"):
        url = base + url
    return PlannerItem(
        plannable_id=int(d.get("plannable_id", 0)),
        plannable_type=d.get("plannable_type", ""),
        course_id=int(d.get("course_id", 0)),
        html_url=url,
        due_at=due,
        title=title,
        raw=d,
    )
