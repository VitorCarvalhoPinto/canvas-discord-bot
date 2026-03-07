"""Scheduled tasks: poll Canvas and post to Discord (#news and #prazos)."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import discord

import cache
from canvas.client import CanvasClient
from canvas.models import Announcement, Assignment, PlannerItem
from discord_bot.embeds import embed_announcement, embed_reminder
from storage import Storage

logger = logging.getLogger(__name__)


async def run_announcements_task(
    bot: discord.Client,
    canvas_client: CanvasClient,
    storage: Storage,
    course_list: List[Tuple[int, str]],
    channel_news_id: int,
) -> int:
    """For each course, fetch announcements; post new ones to #news. Returns count posted."""
    if not channel_news_id:
        return 0
    channel = bot.get_channel(channel_news_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        logger.warning("News channel %s not found or not text channel", channel_news_id)
        return 0
    count = 0
    for course_id, course_name in course_list:
        try:
            announcements = await cache.get_or_fetch(
                f"announcements:{course_id}",
                lambda cid=course_id: canvas_client.get_announcements(cid),
            )
            announcements = sorted(announcements, key=lambda a: (a.created_at or ""))
            for ann in announcements:
                if storage.announcement_sent(ann.id):
                    continue
                embed = embed_announcement(ann, course_name)
                await channel.send(embed=embed)
                storage.mark_announcement_sent(ann.id)
                count += 1
        except Exception as e:
            logger.warning("Announcements task course %s: %s", course_id, e)
    return count


def _parse_due(due_at: Optional[str]):
    if not due_at:
        return None
    try:
        return datetime.fromisoformat(due_at.replace("Z", "+00:00"))
    except Exception:
        return None


async def run_reminders_task(
    bot: discord.Client,
    canvas_client: CanvasClient,
    storage: Storage,
    course_list: List[Tuple[int, str]],
    channel_prazos_id: int,
    days_before: int,
) -> None:
    """For each course, fetch assignments and planner items; post reminders for due within days_before."""
    if not channel_prazos_id:
        return
    channel = bot.get_channel(channel_prazos_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        logger.warning("Prazos channel %s not found or not text channel", channel_prazos_id)
        return
    now = datetime.utcnow()
    if now.tzinfo:
        now = now.replace(tzinfo=None)
    window_end = now + timedelta(days=days_before)
    for course_id, course_name in course_list:
        try:
            assignments = await cache.get_or_fetch(
                f"assignments:{course_id}:upcoming",
                lambda cid=course_id: canvas_client.get_assignments(
                    cid, bucket="upcoming", order_by="due_at"
                ),
            )
            for a in assignments:
                due_dt = _parse_due(a.due_at)
                if not due_dt:
                    continue
                due_utc = due_dt.replace(tzinfo=None) if due_dt.tzinfo else due_dt
                if now <= due_utc <= window_end:
                    key = Storage.reminder_key("assignment", a.id, course_id)
                    if storage.reminder_sent(key):
                        continue
                    embed = embed_reminder(a.name, course_name, a.due_at, a.html_url)
                    await channel.send(embed=embed)
                    storage.mark_reminder_sent(key)
            planner_items = await cache.get_or_fetch(
                f"planner:{course_id}",
                lambda cid=course_id: canvas_client.get_planner_items(
                    cid, filter_incomplete=True
                ),
            )
            for p in planner_items:
                due_dt = _parse_due(p.due_at)
                if not due_dt:
                    continue
                due_utc = due_dt.replace(tzinfo=None) if due_dt.tzinfo else due_dt
                if now <= due_utc <= window_end:
                    key = Storage.reminder_key(
                        p.plannable_type, p.plannable_id, course_id
                    )
                    if storage.reminder_sent(key):
                        continue
                    embed = embed_reminder(
                        p.title, course_name, p.due_at, p.html_url
                    )
                    await channel.send(embed=embed)
                    storage.mark_reminder_sent(key)
        except Exception as e:
            logger.warning("Reminders task course %s: %s", course_id, e)
