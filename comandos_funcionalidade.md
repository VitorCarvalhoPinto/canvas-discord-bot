# Mapeamento dos comandos – Canvas Discord Bot

Documentação de cada comando slash: como funciona e o que faz exatamente.

---

## Comandos de uso geral

### `/proximas-entregas` [dias]

**O que faz:** Lista as próximas entregas (assignments e itens do planner) de todos os cursos monitorados pelo bot.

**Como funciona:**
1. Obtém a lista de cursos (via `course_resolver`: API Canvas ou `CANVAS_COURSE_IDS`).
2. Para cada curso, chama a API Canvas: `get_assignments(course_id, bucket="upcoming", order_by="due_at")` e `get_planner_items(course_id, filter_incomplete=True)`.
3. Se o parâmetro opcional `dias` for informado (número > 0), filtra apenas itens com prazo dentro dos próximos N dias.
4. Monta um embed com título "Próximas entregas", listando cada item com nome, curso, data de entrega e link para o Canvas. Evita duplicatas (mesmo item em assignments e planner).
5. Resposta visível a todos no canal (não é efêmera).

**Parâmetros:**
- `dias` (opcional): inteiro; restringe a entregas com prazo nos próximos N dias.

---

### `/avisos` [curso]

**O que faz:** Lista os últimos avisos (announcements) dos cursos monitorados, com opção de filtrar por um curso.

**Como funciona:**
1. Obtém a lista de cursos.
2. Se o parâmetro `curso` for informado, filtra os cursos por nome (match parcial, case-insensitive) ou por ID exato. Se não houver match, responde "Curso não encontrado" e sugere cursos disponíveis.
3. Para cada curso (ou só o filtrado), chama `get_announcements(course_id)` na API Canvas.
4. Ordena todos os avisos por data de criação (crescente) e mantém apenas os últimos 15.
5. Monta um embed "Últimos avisos" com título do aviso, nome do curso, data e link para o Canvas.
6. Resposta visível a todos no canal.

**Parâmetros:**
- `curso` (opcional): texto; filtra por nome ou ID do curso.

---

### `/cursos`

**O que faz:** Lista os cursos que o bot está monitorando (os mesmos usados para avisos e entregas).

**Como funciona:**
1. Chama `course_resolver()` (lista em cache ou busca via `GET /users/self/courses` / `CANVAS_COURSE_IDS`).
2. Monta um embed "Cursos monitorados" com uma linha por curso: nome do curso (sem exibir ID).
3. Resposta visível a todos no canal.

**Parâmetros:** Nenhum.

---

### `/ajuda`

**O que faz:** Mostra um resumo dos comandos disponíveis do bot.

**Como funciona:**
1. Envia um embed fixo com título "Comandos do bot Canvas" e uma lista em texto dos comandos e suas descrições curtas (proximas-entregas, avisos, cursos, ajuda, debug-news-refresh, debug-news-check).
2. Resposta visível a todos no canal.

**Parâmetros:** Nenhum.

---

## Comandos de debug (#news)

### `/debug-news-refresh`

**O que faz:** Limpa completamente o canal #news, zera no storage os IDs de avisos já enviados e reenvia todos os avisos (como na primeira execução).

**Como funciona:**
1. Verifica se `CHANNEL_NEWS_ID` está configurado e se o canal existe e é de texto.
2. Faz purge de todas as mensagens do canal: em loop, `channel.purge(limit=100)` até não restar mensagem. Requer permissão "Gerenciar mensagens" no canal.
3. Chama `storage.clear_announcement_ids()` (apenas avisos; lembretes de prazos não são afetados).
4. Obtém a lista de cursos e chama `run_announcements_task(...)`: para cada curso, busca avisos na API, ordena por data (mais antigo primeiro) e posta cada aviso no #news, marcando no storage.
5. Responde só para quem executou (efêmero) com confirmação, ex.: "Canal #news limpo (X mensagens removidas) e avisos reenviados." Em caso de falha (canal não configurado, sem permissão, etc.), envia mensagem de erro também efêmera.

**Parâmetros:** Nenhum.

**Requisito:** Bot com permissão "Gerenciar mensagens" no canal #news.

---

### `/debug-news-check`

**O que faz:** Dispara uma única vez a verificação de notícias (mesma lógica usada no polling e no horário das 18h), sem limpar o canal nem o storage.

**Como funciona:**
1. Verifica se o canal #news está configurado.
2. Obtém a lista de cursos e chama `run_announcements_task(...)`: busca avisos por curso na API e posta no #news apenas os que ainda não constam no storage (não reenvia avisos já enviados).
3. Responde só para quem executou (efêmero): "Verificação de notícias executada." ou mensagem de erro.

**Parâmetros:** Nenhum.

**Uso típico:** Testar se novos avisos estão sendo detectados e postados sem esperar o intervalo de polling nem o horário diário.

---

## Resumo rápido

| Comando | Visibilidade | O que faz |
|--------|---------------|-----------|
| `/proximas-entregas` [dias] | Pública | Lista próximas entregas (e opcionalmente filtra por dias). |
| `/avisos` [curso] | Pública | Lista últimos avisos (opcionalmente por curso). |
| `/cursos` | Pública | Lista cursos monitorados. |
| `/ajuda` | Pública | Mostra a lista de comandos. |
| `/debug-news-refresh` | Efêmera | Limpa #news, zera avisos no storage e reenvia todos. |
| `/debug-news-check` | Efêmera | Roda a verificação de notícias uma vez (só envia avisos novos). |
