# Orbit Chat

A small, responsive chatbot built with FastAPI, SQLite, and the Google Gemini API. Send messages through the browser UI, receive model responses, and keep a local history of conversations.

[Interview and architecture guide](./INTERVIEW_GUIDE.md) — technology stack, request flow, build steps, use cases, and interview-ready explanations.

## Features

- Responsive browser-based chat UI at `/`
- Gemini-powered responses through `POST /api/run-automation`
- SQLite storage for prompts and responses
- Conversation history at `GET /api/logs`
- Health check at `GET /health`
- Interactive API documentation at `/docs`

## Requirements

- Python 3.10 or newer
- A Google Gemini API key

## Run locally on Windows

Open PowerShell in this project folder:

```powershell
cd D:\moc-agent-1
```

Create a virtual environment if needed, then install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create a local `.env` file from the example and add your API key:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `GEMINI_API_KEY` in `.env` to your own key. Do not commit or share `.env`.

Start the server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Alternatively, run `start_app.bat` from the project folder.

Open these URLs while the server is running:

- Chat UI: <http://127.0.0.1:8000/>
- API docs: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

Stop the server with **Ctrl+C** in its terminal.

## Send a chat request

The browser UI sends requests for you. You can also use the API docs or PowerShell:

```powershell
$body = @{
    task_name = "greeting"
    user_prompt = "Write a friendly one-sentence greeting."
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/run-automation" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

The result contains the generated answer. Requests and responses are stored in the local SQLite database.

## Database

By default, the app creates `automation.db` in its working directory when it starts. Set `DATABASE_URL` in `.env` to use a different SQLAlchemy-supported database URL. The local database file is ignored by Git because it may contain private prompts and responses.

To list saved records, open `/docs` and call `GET /api/logs`, or use a SQLite viewer on `automation.db`.

## Smoke test

With the server running and a valid Gemini key configured, run:

```powershell
.\.venv\Scripts\python.exe api_smoke_test.py
```

This makes a real Gemini request and saves it to the database.

## Project files

```text
.
├── database.py        # SQLAlchemy model, SQLite setup, and log operations
├── main.py            # FastAPI application and API routes
├── static/
│   └── index.html     # Responsive chatbot interface
├── api_smoke_test.py  # Live API smoke test
├── requirements.txt   # Python dependencies
├── start_app.bat      # Windows server launcher
└── .env.example       # Environment-variable template
```

## Security notes

- Keep API keys in `.env`; never commit secrets.
- Chat prompts and model responses are stored locally in the database.
- The development server binds to `127.0.0.1` by default and is intended for local use. Review authentication, rate limiting, and deployment configuration before exposing it publicly.

## License

No license has been selected yet. Add a `LICENSE` file before publishing if you want to grant others permission to use, modify, or distribute this project.
