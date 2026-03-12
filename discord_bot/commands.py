"""Slash commands for the Canvas bot."""
import logging
from typing import Awaitable, Callable, Dict, List, Tuple

import discord
from discord import app_commands

import cache
import config
from canvas.client import CanvasClient
from canvas.models import Announcement, Assignment
from discord_bot.embeds import embed_avisos, embed_cursos, embed_proximas_entregas
from discord_bot.tasks import run_announcements_task
from storage import Storage

logger = logging.getLogger(__name__)

MSG_INDISPONIVEL = "O bot está temporariamente indisponível. Tente novamente mais tarde."


async def get_course_ids_and_names(
    client: CanvasClient, config_course_ids: List[int]
) -> List[Tuple[int, str]]:
    """Resolve list of (course_id, course_name)."""
    if config_course_ids:
        courses: List[Tuple[int, str]] = [(cid, f"Curso {cid}") for cid in config_course_ids]
        try:
            all_courses = await cache.get_or_fetch("courses", client.get_courses)
            name_by_id = {c.id: c.name for c in all_courses}
            return [(cid, name_by_id.get(cid, f"Curso {cid}")) for cid, _ in courses]
        except Exception:
            return courses
    all_courses = await cache.get_or_fetch("courses", client.get_courses)
    return [(c.id, c.name) for c in all_courses]


def setup_proximas_entregas(
    tree: app_commands.CommandTree,
    canvas_client: CanvasClient,
    course_resolver: Callable[[], Awaitable[List[Tuple[int, str]]]],
) -> None:
    """Register /proximas-entregas slash command."""

    @tree.command(name="proximas-entregas", description="Lista próximas entregas por curso")
    @app_commands.describe(dias="Filtrar por prazo nos próximos N dias (opcional)")
    async def proximas_entregas(interaction: discord.Interaction, dias: int = None):
        await interaction.response.defer(ephemeral=True)
        try:
            course_list = await course_resolver()
            if not course_list:
                await interaction.followup.send(
                    "Nenhum curso configurado. Defina CANVAS_COURSE_IDS ou use um token com cursos.",
                    ephemeral=True,
                )
                return
            course_name_by_id: Dict[int, str] = {cid: name for cid, name in course_list}
            all_assignments: List[Assignment] = []
            for course_id, _ in course_list:
                try:
                    assignments = await cache.get_or_fetch(
                        f"assignments:{course_id}:upcoming",
                        lambda cid=course_id: canvas_client.get_assignments(
                            cid, bucket="upcoming", order_by="due_at"
                        ),
                    )
                    all_assignments.extend(assignments)
                except Exception as e:
                    logger.warning("Error fetching course %s: %s", course_id, e)
            if dias is not None and dias > 0:
                from datetime import datetime, timedelta
                cutoff = datetime.utcnow() + timedelta(days=dias)
                def due_ok(d):
                    if not d:
                        return False
                    try:
                        dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
                        return dt <= cutoff
                    except Exception:
                        return True
                all_assignments = [a for a in all_assignments if due_ok(a.due_at)]
            embed = embed_proximas_entregas(all_assignments, course_name_by_id)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.exception("proximas_entregas error")
            await interaction.followup.send(MSG_INDISPONIVEL, ephemeral=True)


AVISOS_LIMIT = 15


def setup_avisos(
    tree: app_commands.CommandTree,
    canvas_client: CanvasClient,
    course_resolver: Callable[[], Awaitable[List[Tuple[int, str]]]],
) -> None:
    """Register /avisos slash command."""

    @tree.command(name="avisos", description="Lista últimos avisos (opcional: filtrar por curso)")
    @app_commands.describe(curso="Filtrar por nome ou ID do curso (opcional)")
    async def avisos(interaction: discord.Interaction, curso: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            course_list = await course_resolver()
            if not course_list:
                await interaction.followup.send(
                    "Nenhum curso configurado.",
                    ephemeral=True,
                )
                return
            if curso and curso.strip():
                q = curso.strip().lower()
                filtered = [
                    (cid, name)
                    for cid, name in course_list
                    if q in name.lower() or str(cid) == q
                ]
                if not filtered:
                    course_names = ", ".join(name for _, name in course_list[:10])
                    await interaction.followup.send(
                        f"Curso não encontrado. Cursos disponíveis: {course_names}",
                        ephemeral=True,
                    )
                    return
                course_list = filtered
            course_name_by_id = {cid: name for cid, name in course_list}
            all_announcements: List[Announcement] = []
            for course_id, _ in course_list:
                try:
                    anns = await cache.get_or_fetch(
                        f"announcements:{course_id}",
                        lambda cid=course_id: canvas_client.get_announcements(cid),
                    )
                    all_announcements.extend(anns)
                except Exception as e:
                    logger.warning("Error fetching announcements course %s: %s", course_id, e)
            all_announcements = sorted(
                all_announcements,
                key=lambda a: (a.created_at or ""),
            )
            all_announcements = all_announcements[-AVISOS_LIMIT:]
            embed = embed_avisos(all_announcements, course_name_by_id)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.exception("avisos error")
            await interaction.followup.send(MSG_INDISPONIVEL, ephemeral=True)


def setup_cursos(
    tree: app_commands.CommandTree,
    canvas_client: CanvasClient,
    course_resolver: Callable[[], Awaitable[List[Tuple[int, str]]]],
) -> None:
    """Register /cursos slash command."""

    @tree.command(name="cursos", description="Lista cursos monitorados pelo bot")
    async def cursos(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            course_list = await course_resolver()
            if not course_list:
                await interaction.followup.send(
                    "Nenhum curso configurado.",
                    ephemeral=True,
                )
                return
            rows: List[Tuple[int, str, int, int]] = []
            for course_id, name in course_list:
                n_tarefas = n_testes = 0
                try:
                    assignments = await cache.get_or_fetch(
                        f"assignments:{course_id}:all",
                        lambda cid=course_id: canvas_client.get_assignments(cid, bucket=None),
                    )
                    n_tarefas = len(assignments)
                except Exception as e:
                    logger.warning("Error fetching assignments course %s: %s", course_id, e)
                try:
                    quizzes = await cache.get_or_fetch(
                        f"quizzes:{course_id}",
                        lambda cid=course_id: canvas_client.get_quizzes(cid),
                    )
                    n_testes = len(quizzes)
                except Exception as e:
                    logger.warning("Error fetching quizzes course %s: %s", course_id, e)
                rows.append((course_id, name, n_tarefas, n_testes))
            embed = embed_cursos(rows)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.exception("cursos error")
            await interaction.followup.send(MSG_INDISPONIVEL, ephemeral=True)


PREF_BUTTON_PREFIX = "pref:"


def _make_preferencias_view() -> "PreferenciasView":
    """Build PreferenciasView from config.ROLE_PREFERENCES."""
    role_map: Dict[str, int] = {}
    label_map: Dict[str, str] = {}
    for suffix, label, role_id in config.ROLE_PREFERENCES:
        role_map[suffix] = role_id
        label_map[suffix] = label
    return PreferenciasView(role_map, label_map)


class PreferenciasView(discord.ui.View):
    """View with buttons for development preference roles. Toggle: add/remove role. Ephemeral feedback."""

    def __init__(
        self,
        role_map: Dict[str, int],
        label_map: Dict[str, str],
    ):
        super().__init__(timeout=None)
        self._role_map = role_map
        self._label_map = label_map
        for suffix in role_map:
            custom_id = f"{PREF_BUTTON_PREFIX}{suffix}"

            async def btn_callback(interaction: discord.Interaction, suf: str = suffix):
                await self._handle_button(interaction, f"{PREF_BUTTON_PREFIX}{suf}")

            btn = discord.ui.Button(
                label=label_map[suffix],
                custom_id=custom_id,
                style=discord.ButtonStyle.primary,
            )
            btn.callback = btn_callback
            self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def _handle_button(self, interaction: discord.Interaction, custom_id: str):
        await interaction.response.defer(ephemeral=True)
        suffix = custom_id[len(PREF_BUTTON_PREFIX) :]
        if suffix not in self._role_map:
            await interaction.followup.send("Cargo não configurado.", ephemeral=True)
            return
        role_id = self._role_map[suffix]
        label = self._label_map.get(suffix, suffix)
        guild = interaction.guild
        if not guild:
            await interaction.followup.send(
                "Este comando só funciona em um servidor.",
                ephemeral=True,
            )
            return
        member = interaction.user
        if isinstance(member, discord.User):
            member = guild.get_member(member.id)
        if not member:
            await interaction.followup.send(
                "Não foi possível obter seu cargo.",
                ephemeral=True,
            )
            return
        try:
            new_role = guild.get_role(role_id)
            if not new_role:
                await interaction.followup.send(
                    f"Cargo '{label}' não encontrado no servidor.",
                    ephemeral=True,
                )
                return
            if new_role in member.roles:
                await member.remove_roles(new_role)
                msg = f"Você mudou de ideia sobre sua preferência em **{label}**."
            else:
                await member.add_roles(new_role)
                msg = f"Você prefere trabalhar com **{label}**!."
            await interaction.followup.send(msg, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                "Sem permissão para gerenciar cargos. Verifique se o cargo do bot está acima dos cargos de preferência.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            logger.exception("preferencias button error")
            await interaction.followup.send(
                f"Erro ao atribuir cargo: {e}",
                ephemeral=True,
            )


def setup_preferencias(tree: app_commands.CommandTree, bot: discord.Client) -> None:
    """Register persistent View for preference role buttons (no slash command)."""
    if config.ROLE_PREFERENCES:
        persistent_view = _make_preferencias_view()
        bot.add_view(persistent_view)


async def ensure_preferencias_channel_message(
    bot: discord.Client, storage: Storage
) -> None:
    """Ensure the preferencias embed with buttons exists in CHANNEL_PREFERENCIAS_ID."""
    if not config.CHANNEL_PREFERENCIAS_ID or not config.ROLE_PREFERENCES:
        return
    try:
        channel = await bot.fetch_channel(config.CHANNEL_PREFERENCIAS_ID)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        stored_id = storage.get_preferencias_message_id()
        if stored_id:
            try:
                msg = await channel.fetch_message(stored_id)
                if msg and msg.author == bot.user:
                    return
            except (discord.NotFound, discord.HTTPException):
                pass
        embed = discord.Embed(
            title="Preferências de desenvolvimento",
            description=(
                "Clique nos botões abaixo para escolher suas áreas de preferência no desenvolvimento do jogo. "
                "Você pode selecionar múltiplos cargos."
            ),
            color=discord.Color(0x3B82F6),
        )
        view = _make_preferencias_view()
        message = await channel.send(embed=embed, view=view)
        storage.set_preferencias_message_id(message.id)
        logger.info("Posted preferencias message in channel %s", config.CHANNEL_PREFERENCIAS_ID)
    except discord.Forbidden:
        logger.warning("No permission to post in preferencias channel %s", config.CHANNEL_PREFERENCIAS_ID)
    except Exception as e:
        logger.exception("ensure_preferencias_channel_message: %s", e)


def setup_limpar_chat(tree: app_commands.CommandTree) -> None:
    """Register /limpar-chat slash command."""

    @tree.command(
        name="clear",
        description="Limpa mensagens do canal atual (requer cargo Admin)",
    )
    @app_commands.describe(
        quantidade="Quantidade de mensagens a remover (padrão: todas). Máx 100 por vez."
    )
    @app_commands.default_permissions(administrator=True)
    async def limpar_chat(interaction: discord.Interaction, quantidade: int = None):
        await interaction.response.defer(ephemeral=True)
        try:
            channel = interaction.channel
            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.followup.send(
                    "Este comando só funciona em canais de texto.",
                    ephemeral=True,
                )
                return
            purged = 0
            remaining = quantidade if quantidade and quantidade > 0 else None
            while True:
                limit = min(remaining, 100) if remaining else 100
                deleted = await channel.purge(limit=limit)
                if not deleted:
                    break
                purged += len(deleted)
                if remaining is not None:
                    remaining -= len(deleted)
                    if remaining <= 0:
                        break
            await interaction.followup.send(
                f"{purged} mensagem(ns) removida(s).",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Sem permissão para gerenciar mensagens neste canal.",
                ephemeral=True,
            )
        except Exception as e:
            logger.exception("limpar_chat error")
            await interaction.followup.send(
                f"Erro: {e}",
                ephemeral=True,
            )


def setup_debug_cache(tree: app_commands.CommandTree) -> None:
    """Register /debug-cache-clear slash command."""

    @tree.command(
        name="debug-cache-clear",
        description="Debug: limpa o cache de respostas do Canvas.",
    )
    @app_commands.default_permissions(administrator=True)
    async def debug_cache_clear(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            cache.clear()
            await interaction.followup.send("Cache limpo.", ephemeral=True)
        except Exception as e:
            logger.exception("debug_cache_clear error")
            await interaction.followup.send(f"Erro: {e}", ephemeral=True)


def setup_ajuda(tree: app_commands.CommandTree) -> None:
    """Register /help and /help-adm slash commands."""

    @tree.command(name="help", description="Mostra os comandos disponíveis")
    async def ajuda(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Comandos do bot Canvas",
            description=(
                "**/proximas-entregas** [dias] — Lista de tarefas (opcional: próximos N dias).\n"
                "**/avisos** [curso] — Lista últimos avisos (opcional: filtrar por curso).\n"
                "**/cursos** — Lista cursos monitorados.\n"
                "**/help** — Mostra esta mensagem."
            ),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @tree.command(name="help-adm", description="Mostra todos os comandos (incluindo Admin)")
    @app_commands.default_permissions(administrator=True)
    async def ajuda_adm(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Comandos do bot Canvas (Admin)",
            description=(
                "**/proximas-entregas** [dias] — Lista de tarefas (opcional: próximos N dias).\n"
                "**/avisos** [curso] — Lista últimos avisos (opcional: filtrar por curso).\n"
                "**/cursos** — Lista cursos monitorados.\n"
                "**/help** — Mostra comandos disponíveis para todos.\n"
                "**/help-adm** — Mostra esta mensagem (requer cargo Admin).\n"
                "**/clear** [quantidade] — Limpa mensagens do canal atual (requer cargo Admin).\n"
                "**/debug-cache-clear** — Debug: limpa o cache do Canvas.\n"
                "**/debug-news-refresh** — Debug: limpa o canal #news e reenvia todos os avisos.\n"
                "**/debug-news-check** — Debug: executa a verificação de notícias agora (sem esperar horário/intervalo)."
            ),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)


def setup_debug_news(
    tree: app_commands.CommandTree,
    bot: discord.Client,
    canvas_client: CanvasClient,
    storage: Storage,
    course_resolver: Callable[[], Awaitable[List[Tuple[int, str]]]],
    channel_news_id: int,
) -> None:
    """Register debug slash commands for #news."""

    @tree.command(
        name="debug-news-refresh",
        description="Debug: limpa o canal #news e reenvia todos os avisos.",
    )
    @app_commands.default_permissions(administrator=True)
    async def debug_news_refresh(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            if not channel_news_id:
                await interaction.followup.send(
                    "Canal #news não configurado (CHANNEL_NEWS_ID).",
                    ephemeral=False,
                )
                return
            channel = bot.get_channel(channel_news_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.followup.send(
                    "Canal #news não encontrado ou não é um canal de texto.",
                    ephemeral=False,
                )
                return
            purged = 0
            while True:
                deleted = await channel.purge(limit=100)
                if not deleted:
                    break
                purged += len(deleted)
            storage.clear_announcement_ids()
            course_list = await course_resolver()
            if not course_list:
                await interaction.followup.send(
                    "Nenhum curso configurado. Canal limpo e storage zerado.",
                    ephemeral=False,
                )
                return
            posted = await run_announcements_task(
                bot, canvas_client, storage, course_list, channel_news_id
            )
            await interaction.followup.send(
                f"Canal #news limpo ({purged} mensagens removidas) e {posted} aviso(s) reenviado(s).",
                ephemeral=False,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Sem permissão para gerenciar mensagens no canal #news.",
                ephemeral=False,
            )
        except Exception as e:
            logger.exception("debug_news_refresh error")
            await interaction.followup.send(
                f"Erro: {e}",
                ephemeral=False,
            )

    @tree.command(
        name="debug-news-check",
        description="Debug: executa a verificação de notícias agora (sem esperar horário/intervalo).",
    )
    @app_commands.default_permissions(administrator=True)
    async def debug_news_check(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            if not channel_news_id:
                await interaction.followup.send(
                    "Canal #news não configurado (CHANNEL_NEWS_ID).",
                    ephemeral=False,
                )
                return
            course_list = await course_resolver()
            if not course_list:
                await interaction.followup.send(
                    "Nenhum curso configurado.",
                    ephemeral=False,
                )
                return
            posted = await run_announcements_task(
                bot, canvas_client, storage, course_list, channel_news_id
            )
            if posted > 0:
                msg = f"{posted} aviso(s) novo(s) postado(s) no #news."
            else:
                msg = "Nenhum aviso novo."
            await interaction.followup.send(msg, ephemeral=False)
        except Exception as e:
            logger.exception("debug_news_check error")
            await interaction.followup.send(
                f"Erro: {e}",
                ephemeral=False,
            )
