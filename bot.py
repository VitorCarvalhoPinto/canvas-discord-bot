"""Entry point: Canvas Discord bot with polling and slash commands."""
import asyncio
import logging
from typing import List, Tuple

import discord
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from canvas.client import CanvasClient
from discord_bot.commands import (
    ensure_preferencias_channel_message,
    get_course_ids_and_names,
    setup_ajuda,
    setup_avisos,
    setup_cursos,
    setup_debug_cache,
    setup_debug_news,
    setup_limpar_chat,
    setup_preferencias,
    setup_proximas_entregas,
)
from discord_bot.tasks import run_announcements_task, run_reminders_task
from storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# Set in main() / on_ready
_canvas_client: CanvasClient = None
_storage: Storage = None
_discord_bot: discord.Client = None
_course_list_cache: List[Tuple[int, str]] = []


async def resolve_courses() -> List[Tuple[int, str]]:
    """Return list of (course_id, course_name), using config or API."""
    global _course_list_cache
    if _canvas_client is None:
        return []
    _course_list_cache = await get_course_ids_and_names(
        _canvas_client, config.CANVAS_COURSE_IDS
    )
    return _course_list_cache


async def course_resolver() -> List[Tuple[int, str]]:
    """Course list for commands; use cache or refresh."""
    if _course_list_cache:
        return _course_list_cache
    return await resolve_courses()


async def poll_announcements():
    """Job: post new announcements to #news."""
    global _course_list_cache
    if not _course_list_cache:
        await resolve_courses()
    if not _course_list_cache or not _discord_bot:
        return
    await run_announcements_task(
        _discord_bot,
        _canvas_client,
        _storage,
        _course_list_cache,
        config.CHANNEL_NEWS_ID,
    )


async def poll_reminders():
    """Job: post deadline reminders to #prazos."""
    global _course_list_cache
    if not _course_list_cache:
        await resolve_courses()
    if not _course_list_cache or not _discord_bot:
        return
    await run_reminders_task(
        _discord_bot,
        _canvas_client,
        _storage,
        _course_list_cache,
        config.CHANNEL_PRAZOS_ID,
        config.REMINDER_DAYS_BEFORE,
    )


def main():
    global _canvas_client, _storage, _discord_bot

    logger.info("BOT BUILD 2026-03-06 debug")
    if not config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set")
        return
    if not config.CANVAS_TOKEN:
        logger.error("CANVAS_TOKEN not set")
        return

    _canvas_client = CanvasClient(config.CANVAS_BASE_URL, config.CANVAS_TOKEN)
    _storage = Storage()

    intents = discord.Intents.default()
    # Não usar message_content (privileged intent); o bot só posta e responde a slash commands
    bot = discord.Client(intents=intents)
    _discord_bot = bot
    tree = app_commands.CommandTree(bot)

    @bot.event
    async def on_ready():
        logger.info("Bot ready as %s", bot.user)
        await resolve_courses()
        logger.info("Courses: %s", [c[1] for c in _course_list_cache])
        setup_proximas_entregas(tree, _canvas_client, course_resolver)
        setup_avisos(tree, _canvas_client, course_resolver)
        setup_cursos(tree, _canvas_client, course_resolver)
        setup_ajuda(tree)
        setup_preferencias(tree, bot)
        await ensure_preferencias_channel_message(bot, _storage)
        setup_limpar_chat(tree)
        setup_debug_cache(tree)
        setup_debug_news(
            tree,
            bot,
            _canvas_client,
            _storage,
            course_resolver,
            config.CHANNEL_NEWS_ID,
        )
        # Sync de comandos NÃO é feito aqui (evita rate limit e múltiplos disparos do on_ready).
        # Rode: python deploy_commands.py  (apenas quando alterar/adicionar comandos)
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            poll_announcements,
            "interval",
            minutes=config.POLL_INTERVAL_MINUTES,
            id="announcements",
        )
        scheduler.add_job(
            poll_reminders,
            "interval",
            minutes=config.POLL_INTERVAL_MINUTES,
            id="reminders",
        )
        scheduler.add_job(
            poll_announcements,
            "cron",
            hour=config.NEWS_CHECK_HOUR,
            minute=config.NEWS_CHECK_MINUTE,
            id="news_daily",
        )
        scheduler.start()
        asyncio.create_task(poll_announcements())
        asyncio.create_task(poll_reminders())

    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
