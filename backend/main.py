import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from core.data_connectors.duckdb_connector import duckdb_connector
from core.workflow.graph import workflow_app
from config.settings import settings
from config.prompts import (
    PERSONA_REGISTRY,
    get_persona_examples,
    get_persona_label,
    get_persona_route_preferences,
    get_persona_summary,
)
from storage.database import (
    get_chat_history,
    get_report_artifact,
    get_workflow_state,
    init_db,
    list_report_artifacts,
    list_sessions,
    save_report_artifact,
    save_chat_message,
    save_workflow_state,
)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
UPLOAD_DIR = Path("data") / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
init_db()

class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None
    agent_persona: str = "data_analyst"

class TableInfoResponse(BaseModel):
    tables: list[str]
    previews: dict[str, list[dict[str, Any]]]

class UploadResponse(BaseModel):
    table_name: str
    row_count: int
    tables: list[str]

class SessionHistoryResponse(BaseModel):
    session_id: str
    history: list[dict[str, Any]]
    latest_state: dict[str, Any]

class SessionListResponse(BaseModel):
    sessions: list[str]

class ReportListItem(BaseModel):
    id: int
    session_id: str
    route: str
    title: str
    created_at: str
    chart_paths: list[str]
    report_preview: str

class ReportListResponse(BaseModel):
    reports: list[ReportListItem]

class ReportDetailResponse(BaseModel):
    id: int
    session_id: str
    route: str
    title: str
    created_at: str
    chart_paths: list[str]
    report_content: str

class QueryResponse(BaseModel):
    session_id: str
    report_id: int
    agent_persona: str
    agent_persona_label: str
    route: str
    plan: str
    sql_query: str
    sql_preview_data: dict[str, Any]
    python_code: str
    chart_paths: list[str]
    error: str
    structured_context: dict[str, Any]
    final_report: str


def _format_recent_history(history: list[dict[str, Any]], limit: int = 6) -> str:
    recent_items = history[-limit:]
    if not recent_items:
        return "No prior conversation history."

    formatted_items = []
    for item in recent_items:
        role = item.get("role", "unknown")
        content = item.get("content", "").strip()
        if content:
            formatted_items.append(f"{role}: {content}")
    return "\n".join(formatted_items) if formatted_items else "No prior conversation history."

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

@app.get("/api/v1/sessions", response_model=SessionListResponse)
def get_sessions():
    return SessionListResponse(sessions=list_sessions())

@app.get("/api/v1/sessions/{session_id}", response_model=SessionHistoryResponse)
def get_session_detail(session_id: str):
    return SessionHistoryResponse(
        session_id=session_id,
        history=get_chat_history(session_id),
        latest_state=get_workflow_state(session_id),
    )

@app.get("/api/v1/reports", response_model=ReportListResponse)
def get_reports(session_id: str | None = None):
    return ReportListResponse(reports=[ReportListItem(**item) for item in list_report_artifacts(session_id=session_id)])

@app.get("/api/v1/reports/{report_id}", response_model=ReportDetailResponse)
def get_report_detail(report_id: int):
    report = get_report_artifact(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return ReportDetailResponse(**report)

@app.get("/api/v1/datasets/tables", response_model=TableInfoResponse)
def list_tables():
    tables = duckdb_connector.list_tables()
    previews = {table: duckdb_connector.get_table_preview(table, limit=5) for table in tables}
    return TableInfoResponse(tables=tables, previews=previews)

@app.get("/api/v1/personas")
def list_personas():
    return {
        "personas": [
            {
                "key": key,
                "label": get_persona_label(key),
                "summary": get_persona_summary(key),
                "route_preferences": get_persona_route_preferences(key),
                "example_questions": get_persona_examples(key),
            }
            for key in PERSONA_REGISTRY
        ]
    }

@app.post("/api/v1/datasets/upload", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported.")

    base_name = Path(file.filename or "uploaded_table").stem
    table_name = duckdb_connector.sanitize_table_name(base_name)
    file_path = UPLOAD_DIR / f"{table_name}{suffix}"

    with open(file_path, "wb") as output_file:
        output_file.write(await file.read())

    try:
        row_count = duckdb_connector.load_file(table_name, str(file_path))
    except Exception as exc:
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return UploadResponse(table_name=table_name, row_count=row_count, tables=duckdb_connector.list_tables())

@app.post("/api/v1/analyze", response_model=QueryResponse)
async def analyze_data(request: QueryRequest):
    try:
        session_id = request.session_id or uuid4().hex[:12]
        agent_persona = request.agent_persona if request.agent_persona in PERSONA_REGISTRY else "data_analyst"
        history_before_request = get_chat_history(session_id)
        latest_state = get_workflow_state(session_id)
        session_history_text = _format_recent_history(history_before_request)

        save_chat_message(session_id, "user", request.query)
        initial_state = {
            "messages": [HumanMessage(content=request.query)],
            "agent_persona": agent_persona,
            "session_history_text": session_history_text,
            "structured_context": {
                "session": {
                    "session_id": session_id,
                    "recent_history": history_before_request[-6:],
                    "recent_history_text": session_history_text,
                    "latest_state": latest_state,
                    "agent_persona": agent_persona,
                    "agent_persona_label": get_persona_label(agent_persona),
                }
            },
        }
        
        # Run workflow
        final_state = workflow_app.invoke(initial_state)
        save_chat_message(session_id, "assistant", final_state.get("final_report", ""))
        save_workflow_state(session_id, final_state.get("structured_context", {}))
        report_id = save_report_artifact(
            session_id=session_id,
            route=final_state.get("route", ""),
            report_content=final_state.get("final_report", ""),
            chart_paths=final_state.get("chart_paths", []),
            title=final_state.get("structured_context", {}).get("planner", {}).get("plan", "Analysis Report"),
        )
        
        return QueryResponse(
            session_id=session_id,
            report_id=report_id,
            agent_persona=agent_persona,
            agent_persona_label=get_persona_label(agent_persona),
            route=final_state.get("route", ""),
            plan=final_state.get("plan", ""),
            sql_query=final_state.get("sql_query", ""),
            sql_preview_data=final_state.get("sql_preview_data", {"columns": [], "rows": []}),
            python_code=final_state.get("python_code", ""),
            chart_paths=final_state.get("chart_paths", []),
            error=final_state.get("error", ""),
            structured_context=final_state.get("structured_context", {}),
            final_report=final_state.get("final_report", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
