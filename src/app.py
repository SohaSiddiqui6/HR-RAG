"""FastAPI entrypoint: serves the chat UI and a small JSON API."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from src import config, guardrails
from src.rag_chain import answer_question

app = FastAPI(title="HR-RAG")

# Templates and static assets live at the project root, not next to this module.
app.mount(
    "/static",
    StaticFiles(directory=str(config.ROOT_DIR / "static")),
    name="static",
)
templates = Jinja2Templates(directory=str(config.ROOT_DIR / "templates"))


class Question(BaseModel):
    question: str = ""


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/ask")
def ask(payload: Question):
    ok, reason = guardrails.check_question(payload.question)
    if not ok:
        return JSONResponse(status_code=400, content={"error": reason})

    result = answer_question(payload.question)
    return {
        "answer": guardrails.check_answer(result.text),
        "sources": result.sources,
    }


if __name__ == "__main__":
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
