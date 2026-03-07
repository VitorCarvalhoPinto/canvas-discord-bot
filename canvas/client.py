"""Async HTTP client for Canvas API. All requests use course_id where applicable."""
import logging
from typing import List, Optional

import aiohttp

from canvas.models import (
    Announcement,
    Assignment,
    Course,
    PlannerItem,
    announcement_from_dict,
    assignment_from_dict,
    course_from_dict,
    planner_item_from_dict,
)

logger = logging.getLogger(__name__)


class CanvasClient:
    """Async client for Canvas REST API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None

    async def _session_get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.token}"}
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_json(self, path: str, params: Optional[dict] = None) -> list:
        """GET request; follows Link header pagination and returns combined list."""
        session = await self._session_get()
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        all_data: list = []
        while url:
            async with session.get(url, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if isinstance(data, list):
                    all_data.extend(data)
                else:
                    all_data.append(data)
                # Pagination: next link in Link header
                link = resp.headers.get("Link")
                url = ""
                if link:
                    for part in link.split(","):
                        if 'rel="next"' in part:
                            part = part.strip()
                            if part.startswith("<") and ">" in part:
                                url = part[1 : part.index(">")].strip()
                            break
                params = None  # next URL is full
        return all_data

    async def get_courses(self) -> List[Course]:
        """GET /api/v1/users/self/courses. Returns list of courses for the token user."""
        data = await self._get_json("/users/self/courses")
        return [course_from_dict(d) for d in data]

    async def get_announcements(self, course_id: int) -> List[Announcement]:
        """GET /api/v1/announcements?context_codes[]=course_{id}."""
        data = await self._get_json(
            "/announcements",
            params={"context_codes[]": f"course_{course_id}"},
        )
        return [announcement_from_dict(d) for d in data]

    async def get_assignments(
        self,
        course_id: int,
        bucket: Optional[str] = "upcoming",
        order_by: str = "due_at",
    ) -> List[Assignment]:
        """GET /api/v1/courses/:course_id/assignments. When bucket is None, omit it to get all."""
        params: dict = {}
        if bucket is not None:
            params["bucket"] = bucket
            params["order_by"] = order_by
        data = await self._get_json(
            f"/courses/{course_id}/assignments",
            params=params if params else None,
        )
        result = []
        for d in data:
            d["course_id"] = course_id
            result.append(assignment_from_dict(d))
        return result

    async def get_quizzes(self, course_id: int) -> List[dict]:
        """GET /api/v1/courses/:course_id/quizzes. Returns raw list for count. 404 -> []."""
        try:
            return await self._get_json(f"/courses/{course_id}/quizzes")
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.debug("Quizzes 404 for course %s", course_id)
                return []
            raise

    async def get_planner_items(
        self,
        course_id: int,
        filter_incomplete: bool = True,
    ) -> List[PlannerItem]:
        """GET /api/v1/planner/items?context_codes[]=course_{id}&filter=incomplete_items."""
        params: dict = {"context_codes[]": f"course_{course_id}"}
        if filter_incomplete:
            params["filter"] = "incomplete_items"
        data = await self._get_json("/planner/items", params=params)
        result = []
        for d in data:
            d["course_id"] = course_id
            result.append(planner_item_from_dict(d))
        return result
