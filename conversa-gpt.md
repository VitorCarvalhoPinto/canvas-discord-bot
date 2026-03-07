# Relatório – Integração Canvas API → Discord

## 1. Objetivo

Criar uma integração (bot ou script) para um **servidor Discord** que poste automaticamente informações do **Canvas LMS**, como:

* 📢 Avisos dos cursos
* 📚 Novos módulos
* 📝 Atividades / assignments
* ⏰ Tarefas pendentes

Essas informações serão obtidas através da **API oficial do Canvas**.

---

# 2. Descoberta importante – Endpoint base correto

Durante os testes foi utilizada inicialmente a URL:

```
https://canvas.pucminas.br/api/v1/courses
```

Resultado:

```
404 Not Found
```

Isso ocorre porque o ambiente utilizado está hospedado diretamente na infraestrutura da **Instructure**.

## ✅ Endpoint base correto

```
https://canvas.instructure.com/api/v1
```

Todas as chamadas da API devem utilizar essa base.

Exemplo:

```
https://canvas.instructure.com/api/v1/users/self
```

---

# 3. Autenticação na API

A API do Canvas utiliza **Access Token**.

O token deve ser enviado no header da requisição.

### Header obrigatório

```
Authorization: Bearer ACCESS_TOKEN
```

### Exemplo com curl

```
curl -H "Authorization: Bearer SEU_TOKEN" \
https://canvas.instructure.com/api/v1/users/self
```

---

# 4. Endpoints principais para o projeto

## 4.1 Testar autenticação do usuário

Endpoint usado para verificar se o token está funcionando.

```
GET /api/v1/users/self
```

URL completa:

```
https://canvas.instructure.com/api/v1/users/self
```

---

# 4.2 Listar cursos do aluno

Usado para descobrir o **course_id** necessário para outras chamadas.

```
GET /api/v1/users/self/courses
```

URL:

```
https://canvas.instructure.com/api/v1/users/self/courses
```

### Exemplo de resposta

```json
[
  {
    "id": 123456,
    "name": "Jogos Digitais"
  }
]
```

O campo **id** é o `course_id`.

---

# 4.3 Listar módulos de um curso

```
GET /api/v1/courses/:course_id/modules
```

Exemplo:

```
https://canvas.instructure.com/api/v1/courses/123456/modules
```

---

# 4.4 Listar itens de um módulo

Permite descobrir atividades, páginas e quizzes dentro do módulo.

```
GET /api/v1/courses/:course_id/modules/:module_id/items
```

Exemplo:

```
https://canvas.instructure.com/api/v1/courses/123456/modules/987/items
```

Tipos de conteúdo possíveis:

* Page
* Assignment
* Quiz
* File
* Discussion

---

# 4.5 Avisos (Announcements)

Lista avisos publicados nos cursos.

```
GET /api/v1/announcements
```

Filtrando por curso:

```
GET /api/v1/announcements?context_codes[]=course_123456
```

URL completa:

```
https://canvas.instructure.com/api/v1/announcements?context_codes[]=course_123456
```

---

# 4.6 Timeline de atividades

Endpoint muito útil para bots de notificação.

```
GET /api/v1/users/self/activity_stream
```

URL:

```
https://canvas.instructure.com/api/v1/users/self/activity_stream
```

Retorna:

* novos avisos
* atividades
* discussões
* eventos recentes

---

# 4.7 Tarefas pendentes

Endpoint ideal para avisar prazos de entrega.

```
GET /api/v1/users/self/todo
```

URL:

```
https://canvas.instructure.com/api/v1/users/self/todo
```

Retorna:

* assignments
* quizzes
* atividades com prazo

---

# 5. Arquitetura sugerida do bot

Fluxo de funcionamento:

```
Canvas API
     ↓
Script (Python / Node)
     ↓
Consulta endpoints periodicamente
     ↓
Detecta novidades
     ↓
Envia mensagem via Discord Webhook
     ↓
Canal #news
```

---

# 6. Endpoints essenciais para o projeto

Lista final dos endpoints recomendados:

```
GET /api/v1/users/self
GET /api/v1/users/self/courses
GET /api/v1/courses/:course_id/modules
GET /api/v1/courses/:course_id/modules/:module_id/items
GET /api/v1/announcements
GET /api/v1/users/self/activity_stream
GET /api/v1/users/self/todo
```

Base URL obrigatória:

```
https://canvas.instructure.com/api/v1
```

---

# 7. Documentação oficial

Documentação oficial da API do Canvas:

```
https://canvas.instructure.com/doc/api/
```

---

# 8. Conclusão

A API do Canvas permite implementar um sistema automático de notificações no Discord que pode:

* detectar novos avisos
* identificar novos módulos
* avisar sobre atividades
* alertar prazos de entrega

Com um script simples consultando os endpoints periodicamente e enviando mensagens para o canal **#news** do servidor.
