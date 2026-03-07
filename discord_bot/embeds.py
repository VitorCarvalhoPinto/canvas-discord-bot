"""Build Discord embeds for announcements and reminders."""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import discord

from canvas.models import Announcement, Assignment


def _parse_canvas_date(s: Optional[str]):
    if not s:
        return None
    try:
        # Canvas returns ISO 8601 e.g. 2012-07-01T23:59:00-06:00
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def strip_html(html: str, max_len: int = 500) -> str:
    """Remove HTML tags and truncate."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", "", html).replace("&nbsp;", " ").strip()
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def embed_announcement(announcement: Announcement, course_name: str) -> discord.Embed:
    """Embed for a new announcement to post in #news."""
    embed = discord.Embed(
        title=announcement.title or "Aviso",
        description=strip_html(announcement.message),
        url=announcement.html_url,
        color=discord.Color.blue(),
    )
    embed.set_author(name=course_name)
    ts = _parse_canvas_date(announcement.created_at)
    if ts:
        embed.timestamp = ts
    embed.set_footer(text="Canvas")
    return embed


def embed_reminder(
    title: str,
    course_name: str,
    due_at: Optional[str],
    html_url: str,
) -> discord.Embed:
    """Embed for a deadline reminder to post in #prazos."""
    embed = discord.Embed(
        title=title,
        description=f"**Curso:** {course_name}\n**Link:** [Abrir no Canvas]({html_url})",
        url=html_url,
        color=discord.Color.orange(),
    )
    ts = _parse_canvas_date(due_at)
    if ts:
        embed.timestamp = ts
    elif due_at:
        embed.add_field(name="Prazo", value=due_at, inline=False)
    embed.set_footer(text="Lembrete de entrega")
    return embed


def embed_proximas_entregas(
    assignments: list,
    course_name_by_id: dict,
) -> discord.Embed:
    """Single embed summarizing assignments for /proximas-entregas (Lista de Tarefas)."""
    lines = []
    for a in assignments:
        course_name = course_name_by_id.get(a.course_id, f"Curso {a.course_id}")
        due = a.due_at[:16] if a.due_at else "Sem data"
        lines.append(f"• **{a.name}** — {course_name} — {due}\n  {a.html_url}")

    if not lines:
        return discord.Embed(
            title="Lista de Tarefas",
            description="Nenhuma tarefa encontrada.",
            color=discord.Color.green(),
        )

    # Discord embed description limit is 4096
    desc = "\n".join(lines)
    if len(desc) > 3900:
        desc = desc[:3900] + "\n..."
    return discord.Embed(
        title="Lista de Tarefas",
        description=desc,
        color=discord.Color.green(),
    )


def _course_id_from_context(context_code: str) -> int:
    if context_code and context_code.startswith("course_"):
        try:
            return int(context_code.replace("course_", "", 1))
        except ValueError:
            pass
    return 0


def embed_avisos(
    announcements: List[Announcement],
    course_name_by_id: Dict[int, str],
    limit: int = 4096,
) -> discord.Embed:
    """Embed 'Últimos avisos' com título, curso, data e link (respeitando limite do embed)."""
    lines = []
    for ann in announcements:
        cid = _course_id_from_context(ann.context_code)
        course_name = course_name_by_id.get(cid, f"Curso {cid}")
        date_str = (ann.created_at[:10] if ann.created_at else "") or "—"
        line = f"• **{ann.title or 'Aviso'}** — {course_name} — {date_str}\n  {ann.html_url}"
        lines.append(line)
    desc = "\n".join(lines) if lines else "Nenhum aviso encontrado."
    if len(desc) > limit:
        desc = desc[: limit - 4] + "\n..."
    return discord.Embed(
        title="Últimos avisos",
        description=desc,
        color=discord.Color.blue(),
    )


def embed_cursos(
    course_list: List[Tuple[int, str, int, int]],
) -> discord.Embed:
    """Embed 'Cursos monitorados' com nome e contagens (tarefas, testes)."""
    lines = [
        f"• **{name}** — {n_tarefas} tarefas, {n_testes} testes"
        for _cid, name, n_tarefas, n_testes in course_list
    ]
    desc = "\n".join(lines) if lines else "Nenhum curso configurado."
    return discord.Embed(
        title="Cursos monitorados",
        description=desc,
        color=discord.Color.blue(),
    )
