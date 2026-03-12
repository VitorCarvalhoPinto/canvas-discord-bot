"""
Sincroniza os slash commands com o Discord. Rode apenas quando alterar ou adicionar comandos.

Uso: python deploy_commands.py

Não rode isso toda vez que ligar o bot; use só após mudar comandos para evitar rate limit.
"""
import logging

import discord
from discord import app_commands

import config
from canvas.client import CanvasClient
from discord_bot.commands import (
    setup_ajuda,
    setup_avisos,
    setup_cursos,
    setup_debug_cache,
    setup_debug_news,
    setup_limpar_chat,
    setup_preferencias,
    setup_proximas_entregas,
)
from storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def _empty_course_resolver():
    return []


def main():
    if not config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN não definido no .env")
        return
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    storage = Storage()
    canvas_client = (
        CanvasClient(config.CANVAS_BASE_URL, config.CANVAS_TOKEN)
        if config.CANVAS_TOKEN and config.CANVAS_BASE_URL
        else None
    )

    @client.event
    async def on_ready():
        try:
            setup_proximas_entregas(tree, canvas_client, _empty_course_resolver)
            setup_avisos(tree, canvas_client, _empty_course_resolver)
            setup_cursos(tree, canvas_client, _empty_course_resolver)
            setup_ajuda(tree)
            setup_preferencias(tree, client)
            setup_limpar_chat(tree)
            setup_debug_cache(tree)
            setup_debug_news(
                tree,
                client,
                canvas_client,
                storage,
                _empty_course_resolver,
                config.CHANNEL_NEWS_ID,
            )
            cmds = list(tree.get_commands())
            logger.info("Commands on tree before sync: %s", len(cmds))
            if config.GUILD_ID:
                guild = await client.fetch_guild(config.GUILD_ID)
                if guild:
                    synced = await tree.sync(guild=guild)
                    logger.info("Synced %s command(s) to guild %s", len(synced), config.GUILD_ID)
                else:
                    logger.warning("Guild %s not found", config.GUILD_ID)
            else:
                synced = await tree.sync()
                logger.info("Synced %s command(s) globally", len(synced))
        except Exception as e:
            logger.exception("Sync failed: %s", e)
        await client.close()

    client.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
