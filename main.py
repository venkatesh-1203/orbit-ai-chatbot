from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

try:
    from google import genai
except ImportError:  # pragma: no cover - handled at runtime
    genai = None

from database import db_create_log, db_fetch_all_logs, get_db, init_db

logger = logging.getLogger(__name__)

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class TaskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task_name: str = Field(..., min_length=1, max_length=200)
    user_prompt: str = Field(..., min_length=1, max_length=20000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="MOC Agent",
    description="Generates text with Gemini and stores automation logs.",
    version="1.0.0",
    lifespan=lifespan,
)

ai_client = (
    genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY and genai is not None else None
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/run-automation")
def execute_ai_task(payload: TaskRequest, db: Session = Depends(get_db)):
    if ai_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured.",
        )

    task_name = payload.task_name.strip()
    user_prompt = payload.user_prompt.strip()

    if not task_name or not user_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="task_name and user_prompt must not be empty.",
        )

    try:
        response = ai_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_prompt,
        )
        result = getattr(response, "text", None) or "No content generated."
    except Exception as error:
        logger.exception("Gemini request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini request failed.",
        ) from error

    try:
        log = db_create_log(db, task_name, user_prompt, result)
    except Exception as error:
        logger.exception("Failed to save automation log")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the automation log.",
        ) from error

    return {
        "status": "success",
        "log_id": log.id,
        "task": log.task_name,
        "result": log.ai_response,
    }


@app.get("/api/logs")
def fetch_all_logs(db: Session = Depends(get_db)):
    try:
        logs = db_fetch_all_logs(db)
    except Exception as error:
        logger.exception("Failed to fetch automation logs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch automation logs.",
        ) from error

    return {
        "total_records": len(logs),
        "history": [
            {
                "id": log.id,
                "task_name": log.task_name,
                "prompt_sent": log.prompt_sent,
                "ai_response": log.ai_response,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ],
    }