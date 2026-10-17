# Orbit Chat: Project and Interview Guide

This guide describes the implementation in this repository. Use it to explain the project accurately in an interview; distinguish working features from possible future improvements.

## 1. Project in one sentence

Orbit Chat is a small, locally runnable chatbot: a responsive browser page sends messages to a Python FastAPI backend, the backend asks Google Gemini to generate a response, and SQLite stores the prompt and answer for later review.

## 2. The aim and the user problem

### Plain-language explanation

The aim is to give someone a simple place to ask an AI a question and read its answer, without using an API tool directly. The browser is the chat window, the Python server acts as the secure coordinator, Gemini generates the answer, and a local database keeps a history.

### More technical explanation

The project demonstrates an end-to-end LLM application flow: browser input, JSON over HTTP, server-side validation, third-party model inference, relational persistence, and a JSON response rendered in a responsive UI.

### Example users and use cases

- A learner asks for a plain-language explanation of a concept.
- Someone brainstorming asks for ideas or a starting point.
- A user drafts or improves a routine email.
- A developer demonstrates how to connect a web UI, API, LLM provider, and database.
- A user reviews past prompts and answers through the logs endpoint or a SQLite viewer.

These are general-purpose assistant examples, not claims that the model is guaranteed to be factually correct or suitable for high-stakes decisions.

## 3. Technology stack

| Layer | Technology | How this project uses it |
|---|---|---|
| Language/runtime | Python 3.10+ | Backend routes, database access, configuration, and smoke-test script. |
| Web framework | FastAPI | Defines HTTP routes, dependency injection, request handling, and generated API documentation. |
| ASGI server | Uvicorn | Runs the FastAPI application locally. |
| Request validation | Pydantic | `TaskRequest` validates and trims strings; limits task names to 200 characters and prompts to 20,000 characters. |
| LLM provider | Google Gemini API | Produces text from the user's prompt using the model configured in `main.py` (`gemini-3.8-flash`). Model availability is controlled by Google and may change. |
| Provider SDK | `google-genai` | Python client used to call `models.generate_content`. The API key stays on the server. |
| Persistence/ORM | SQLAlchemy | Maps the `AutomationLog` Python class to a database table and handles sessions, inserts, queries, and schema creation. |
| Database | SQLite | Local file database; default URL is `sqlite:///./automation.db`. |
| Secrets/configuration | `python-dotenv` and environment variables | Loads `GEMINI_API_KEY` and optional `DATABASE_URL` from a local `.env` file. |
| Frontend structure | HTML5 | Defines the page, semantic sections, form, chat messages, suggestions, and accessible labels. |
| Frontend styling | CSS3 | Provides layout, colors, message bubbles, responsive breakpoints, reduced-motion support, and small transitions. |
| Frontend behavior | Vanilla JavaScript | Handles form submission, chat state, loading/error messages, prompt context, and clearing the conversation. No frontend framework or bundler is used. |
| Browser networking | Fetch API, HTTP, JSON | Sends `POST` requests to FastAPI and reads JSON responses; health check uses `GET`. |
| Testing utility | Python standard library (`urllib`, `json`, `time`) | `api_smoke_test.py` waits for the service, checks logs, and sends one live chat request. |
| Source-control hygiene | Git ignore rules | `.gitignore` excludes local credentials, databases, virtual environments, and generated files. |
| Local developer environment | Windows batch file and virtual environment | `start_app.bat` runs Uvicorn; `.venv` isolates installed Python packages. |

The frontend is intentionally dependency-light: there is no React, Vue, Node.js build step, CSS framework, or client-side router.

## 4. Architecture and request flow

```text
User
  │ types a message
  ▼
Browser UI (HTML + CSS + JavaScript)
  │ POST /api/run-automation, JSON
  ▼
FastAPI (main.py)
  ├─ Pydantic validates the request
  ├─ Gemini SDK sends the prompt to Gemini
  ├─ SQLAlchemy stores the prompt and response
  └─ returns JSON with the answer and log ID
       │
       ├────────► Google Gemini API (inference)
       │
       └────────► SQLite file automation.db (history)
  ▼
Browser displays the returned answer
```

### What happens when a user sends a message

1. The user types in the textarea or selects one of the suggested prompts.
2. JavaScript trims the message, shows the user bubble and a “Thinking” indicator, and disables the send button while the request is active.
3. For follow-up turns, the page prepends recent user/assistant messages as plain-text context. It caps this constructed context at roughly 18,000 characters and sends the current turn to the backend as one prompt. The page's conversation state lives in browser memory; refreshing or selecting “New chat” clears it.
4. `fetch` sends JSON to `POST /api/run-automation` on the same server. The payload has `task_name` and `user_prompt`.
5. FastAPI parses the JSON and Pydantic checks that fields are non-empty after whitespace stripping and within the configured length limits.
6. The backend calls Gemini using the server-side API key. The key is never put in the HTML or sent back to the browser.
7. SQLAlchemy inserts one log row. It stores the task name, the actual prompt sent to Gemini (including included conversation context), the generated answer, and a timestamp.
8. FastAPI returns a JSON response containing `status`, `log_id`, `task`, and `result`.
9. JavaScript inserts the answer as text and retains it in the in-memory chat context for the next follow-up.

If Gemini fails, the backend logs diagnostic details to the server terminal and returns a generic HTTP 502. If saving the log fails, it returns HTTP 500. Missing Gemini configuration returns HTTP 503. Invalid request bodies are rejected by FastAPI/Pydantic before generation.

## 5. API endpoints

### `GET /`

Returns the chatbot HTML page from `static/index.html`.

### `GET /health`

Returns `{"status":"ok"}` when the app route is responding. This is a lightweight process/app health check; it does not prove that the Gemini key, provider, or database writes all work.

### `POST /api/run-automation`

Example request:

```json
{
  "task_name": "Chat",
  "user_prompt": "Explain how rainbows form in simple terms."
}
```

Example successful response shape:

```json
{
  "status": "success",
  "log_id": 4,
  "task": "Chat",
  "result": "A rainbow forms when sunlight bends and reflects inside raindrops..."
}
```

The exact answer is generated by Gemini and will vary.

### `GET /api/logs`

Returns the number of log rows and a history list with each row's ID, task name, prompt, answer, and timestamp. `/docs` provides an interactive OpenAPI/Swagger UI for trying these endpoints.

## 6. Database design

The SQLAlchemy `AutomationLog` model maps to the SQLite table `automation_logs`:

| Column | Purpose |
|---|---|
| `id` | Integer primary key. |
| `task_name` | Short label such as `Chat` or `greeting`. |
| `prompt_sent` | The complete prompt sent to the model. |
| `ai_response` | Text returned from Gemini. |
| `timestamp` | UTC timestamp for the saved row. |

The schema is initialized during FastAPI startup. The current code also includes a small SQLite migration: if the older table exists without `task_name`, it adds the column and fills old rows with `Legacy task`. This was needed because SQLAlchemy's `create_all` creates missing tables but does not automatically add new columns to existing tables.

The default SQLite URL is relative to the process working directory. Running Uvicorn from the project folder uses that folder's `automation.db`; setting `DATABASE_URL` can point to another database.

## 7. How the project was built

Use this sequence to describe the implementation work:

1. **Set the project goal.** Build a small assistant that accepts a natural-language prompt and returns an LLM answer.
2. **Choose a minimal architecture.** Use one Python web service, a single-page browser client, a hosted LLM API, and a local SQL database rather than introducing a separate frontend build system or production database.
3. **Create the API.** Add FastAPI routes for the chat operation, health status, chat UI, and persisted logs.
4. **Define request validation.** Use a Pydantic model to require a task name and prompt, trim whitespace, and set maximum sizes.
5. **Connect the model provider.** Load the Gemini API key from `.env`/environment, initialize the Google GenAI client on the server, and call the configured text-generation model.
6. **Add persistence.** Define the SQLAlchemy log model, create the SQLite engine and session dependency, and commit each generated exchange to `automation_logs`.
7. **Handle existing databases.** Add a targeted migration for the older SQLite schema where the task-name field was absent, while retaining existing prompts and answers.
8. **Build the UI.** Use plain HTML, CSS, and JavaScript to make a responsive chat page with suggestions, follow-up context, send/loading states, service status, and error display.
9. **Add local configuration and startup.** Provide `requirements.txt`, `.env.example`, `.gitignore`, and a Windows batch launcher.
10. **Verify behavior.** Exercise routes with FastAPI's test client and a mocked Gemini client for deterministic route and database checks. The separate `api_smoke_test.py` performs a live request and therefore requires a valid key, network access, and an available model.
11. **Document the project.** Describe setup, endpoints, database, limitations, and security considerations in `README.md`.

## 8. Interview-ready explanation

### 30-second version

> “I built Orbit Chat, a small full-stack LLM demo. The frontend is a responsive HTML/CSS/JavaScript chat page. It sends JSON to a FastAPI backend, which validates the prompt with Pydantic, calls Google's Gemini API using a server-side key, then saves the prompt and answer through SQLAlchemy into SQLite. It returns the answer to the browser and provides endpoints for health checks and reviewing logs. I focused on a simple end-to-end flow, request validation, error handling, and keeping credentials out of the frontend.”

### 2-minute version

> “The project is a lightweight web chatbot. A user submits a message in the browser. Vanilla JavaScript keeps the current conversation in memory and includes recent turns as context with follow-up messages. It posts the prompt as JSON to a FastAPI endpoint. Pydantic validates the input, and the backend calls Gemini through Google's Python SDK. The backend then saves the task name, exact prompt, model answer, and UTC timestamp in a SQLite table using SQLAlchemy. Finally, it responds with JSON and the UI renders the answer as text.
>
> “I chose FastAPI because it makes typed request handling and interactive OpenAPI docs quick to build. SQLite is convenient for a local demo with no separate database server, and SQLAlchemy keeps persistence code separate from API handling. The UI uses plain browser technologies to keep the stack easy to run. I added defensive behavior for missing configuration, provider failures, database failures, and an old SQLite schema. The current version is meant as a local prototype; for a public multi-user product I would add authentication, abuse controls, more robust migrations, deployment configuration, and automated tests.”

### Non-technical explanation

> “Think of it like a front desk for an AI assistant. The chat page takes your question and sends it to our Python service. The service checks that the message is usable, forwards it to Google's AI, records the question and answer in a local notebook-like database, and sends the answer back to the page. The key to the AI account stays in the service rather than in the browser.”

## 9. Useful interview questions and honest answers

### Why SQLite?

It is built into Python, easy to run locally, and appropriate for a single-user demonstration. A deployed multi-user system with concurrent writes, backups, and operational requirements would likely use PostgreSQL or another managed database.

### Why FastAPI?

It provides clear route definitions, Pydantic request parsing, dependency injection for database sessions, and generated OpenAPI documentation with little setup.

### Why save the prompt and answer?

It demonstrates persistence and makes it possible to review request history. It also means the database contains user-entered text, so privacy, retention, and access controls matter before using real sensitive data.

### Is this a trained/custom LLM?

No. The application calls a hosted Gemini model. The project does not train or fine-tune a model; it sends prompt text to the provider and displays the generated response.

### How does conversational context work?

The browser stores recent user/assistant turns in memory and includes them as text in the next prompt. The backend does not maintain a formal conversation/session object. The stored row captures the composed prompt and answer for each request.

### Is the chat history restored when I reopen the page?

No. `/api/logs` exposes persisted rows, but the current chat page does not load logs back into a conversation. The active conversation context exists only in that page's JavaScript memory.

### What does the health endpoint verify?

Only that the HTTP application can answer `/health`. It does not test the Gemini API or database write path.

### What happens when something goes wrong?

Request validation errors are returned by FastAPI. Missing Gemini configuration gives 503; provider errors are logged on the server and returned as generic 502 responses; database failures are logged and returned as 500 responses.

### What security choices are present?

The API key is read from an environment variable and not embedded in frontend assets. `.gitignore` excludes `.env` and local database files. Database contents can include private prompts and answers. The current app has no authentication, authorization, rate limiting, or production hardening, so it should not be exposed publicly without additional work.

### What would you improve next?

1. Add automated unit and integration tests that do not require live Gemini calls.
2. Add user accounts and server-side conversation IDs if multi-user history is needed.
3. Add rate limiting, quotas, timeouts, and structured provider error mapping.
4. Use a formal migration tool such as Alembic as schema changes grow.
5. Add configurable model/provider settings, prompt-size limits, and token/cost observability.
6. Add pagination and filtering to the logs endpoint.
7. Add deployment configuration, HTTPS, secret management, privacy/retention controls, and monitoring.
8. Consider streaming tokens for a faster chat experience.

## 10. Run and demonstrate it

From PowerShell in the project directory:

```powershell
cd D:\moc-agent-1
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/> and ask a short question. Keep the server terminal visible to show request logs. Open <http://127.0.0.1:8000/docs> to demonstrate the API and <http://127.0.0.1:8000/health> for the health response. Stop the server with **Ctrl+C**.

Before demoing, confirm the local `.env` contains a valid, private `GEMINI_API_KEY`, and do not show or paste it during the interview.

## 11. Repository map

```text
main.py             FastAPI app, request model, Gemini call, routes
database.py         SQLAlchemy model, engine/session, SQLite migration and queries
static/index.html   Single-page responsive UI (HTML, CSS, and JavaScript)
requirements.txt    Python runtime dependencies
api_smoke_test.py   Live HTTP smoke-test utility
start_app.bat       Windows Uvicorn launcher
.env.example        Safe configuration template; no real key
.gitignore          Excludes secrets, local DBs, virtualenvs, and caches
README.md           Project setup and usage
INTERVIEW_GUIDE.md  This technical and presentation guide
```

## 12. Scope and limitations to disclose

- This is a local prototype, not a production-ready hosted service.
- The UI's conversation context is temporary and held in browser memory.
- One log row is stored for each successful model response; there is no user or conversation table.
- Model output quality, availability, quotas, pricing, and model names depend on the external provider and account.
- The current API call is synchronous from the route's perspective; there is no token streaming.
- The database is local SQLite by default and should be backed up or replaced for deployment.
- No authentication, authorization, rate limiting, or user-specific data isolation is implemented.
- AI answers can be inaccurate and should be reviewed for important decisions.
