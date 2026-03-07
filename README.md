# Canvas Discord Bot

Bot que integra a API do Canvas ao Discord: posta avisos no canal #news e lembrete de prazos no #prazos, e oferece o comando `/proximas-entregas`.

## Requisitos

- Python 3.10+
- Conta Discord com um bot criado no [Developer Portal](https://discord.com/developers/applications)
- Token de acesso da API do Canvas (Instructure)

## Instalação

```bash
cd canvas-discord-bot
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
# Edite .env com DISCORD_TOKEN, CANVAS_TOKEN e IDs dos canais
```

## Configuração (.env)

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| DISCORD_TOKEN | Sim | Token do bot Discord |
| CANVAS_TOKEN | Sim | Access token da API Canvas |
| CANVAS_BASE_URL | Não | Base da API (padrão: https://canvas.instructure.com/api/v1) |
| CHANNEL_NEWS_ID | Sim | ID do canal #news |
| CHANNEL_PRAZOS_ID | Sim | ID do canal #prazos |
| POLL_INTERVAL_MINUTES | Não | Intervalo de polling em minutos (padrão: 15) |
| REMINDER_DAYS_BEFORE | Não | Dias antes do prazo para enviar lembrete (padrão: 2) |
| CANVAS_COURSE_IDS | Não | IDs dos cursos separados por vírgula; se vazio, usa GET /users/self/courses |

Para obter o ID de um canal: ative o Modo Desenvolvedor nas configurações do Discord, clique com o botão direito no canal e "Copiar ID".

## Uso

**Subir o bot:**

```bash
python bot.py
```

**Sincronizar comandos com o Discord** (rode apenas quando adicionar ou alterar slash commands; evita rate limit e múltiplos syncs no `on_ready`):

```bash
python deploy_commands.py
```

Depois de rodar `deploy_commands.py`, reinicie o bot (`python bot.py`) se ele já estiver rodando.

- **#news**: o bot posta automaticamente novos avisos dos cursos (polling por course_id) e também faz uma verificação diária em horário configurável (padrão 18h). Para reenviar **todas** as notícias uma vez (por exemplo na primeira vez ou após limpar o histórico), apague o arquivo `data/sent_ids.json` (ou apague só a chave `announcement_ids` dentro dele) e reinicie o bot; na próxima execução ele enviará todos os avisos e voltará a evitar duplicatas.
- **#prazos**: o bot posta lembretes de entregas X dias antes do prazo; além disso, qualquer um pode usar o comando `/proximas-entregas` (e opcionalmente `/proximas-entregas dias:N`) para listar as próximas entregas por curso.

## Estrutura

- `bot.py` – entrada do bot e agendamento das tarefas
- `deploy_commands.py` – sincroniza os slash commands com o Discord (rodar só quando mudar comandos)
- `config.py` – carrega variáveis do `.env`
- `canvas/` – cliente da API Canvas (cursos, avisos, assignments, planner)
- `discord_bot/` – comandos slash, embeds e tarefas de polling
- `storage.py` – persistência dos IDs já enviados (evita duplicatas)
