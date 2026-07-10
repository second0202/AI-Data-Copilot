from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import json

from config.settings import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String) # user, assistant, system
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkflowState(Base):
    __tablename__ = "workflow_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, unique=True)
    state_data = Column(Text) # JSON serialized state
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReportArtifact(Base):
    __tablename__ = "report_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    route = Column(String)
    title = Column(String)
    report_content = Column(Text)
    chart_paths = Column(Text)  # JSON serialized list
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)


def save_chat_message(session_id: str, role: str, content: str):
    db = SessionLocal()
    try:
        db.add(ChatMessage(session_id=session_id, role=role, content=content))
        db.commit()
    finally:
        db.close()


def get_chat_history(session_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .all()
        )
        return [
            {
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ]
    finally:
        db.close()


def list_sessions(limit: int = 20) -> list[str]:
    db = SessionLocal()
    try:
        rows = (
            db.query(ChatMessage.session_id)
            .distinct()
            .order_by(ChatMessage.session_id.desc())
            .limit(limit)
            .all()
        )
        return [row[0] for row in rows if row[0]]
    finally:
        db.close()


def save_workflow_state(session_id: str, state_data: dict):
    db = SessionLocal()
    try:
        serialized_state = json.dumps(state_data, ensure_ascii=False)
        existing = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
        if existing:
            existing.state_data = serialized_state
            existing.updated_at = datetime.utcnow()
        else:
            db.add(WorkflowState(session_id=session_id, state_data=serialized_state))
        db.commit()
    finally:
        db.close()


def get_workflow_state(session_id: str) -> dict:
    db = SessionLocal()
    try:
        row = db.query(WorkflowState).filter(WorkflowState.session_id == session_id).first()
        if not row or not row.state_data:
            return {}
        return json.loads(row.state_data)
    finally:
        db.close()


def save_report_artifact(
    session_id: str,
    route: str,
    report_content: str,
    chart_paths: list[str] | None = None,
    title: str | None = None,
) -> int:
    db = SessionLocal()
    try:
        artifact = ReportArtifact(
            session_id=session_id,
            route=route,
            title=title or f"Report {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            report_content=report_content,
            chart_paths=json.dumps(chart_paths or [], ensure_ascii=False),
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return artifact.id
    finally:
        db.close()


def list_report_artifacts(session_id: str | None = None, limit: int = 50) -> list[dict]:
    db = SessionLocal()
    try:
        query = db.query(ReportArtifact)
        if session_id:
            query = query.filter(ReportArtifact.session_id == session_id)
        rows = query.order_by(ReportArtifact.created_at.desc(), ReportArtifact.id.desc()).limit(limit).all()
        return [
            {
                "id": row.id,
                "session_id": row.session_id,
                "route": row.route,
                "title": row.title,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "chart_paths": json.loads(row.chart_paths or "[]"),
                "report_preview": (row.report_content or "")[:200],
            }
            for row in rows
        ]
    finally:
        db.close()


def get_report_artifact(report_id: int) -> dict | None:
    db = SessionLocal()
    try:
        row = db.query(ReportArtifact).filter(ReportArtifact.id == report_id).first()
        if not row:
            return None
        return {
            "id": row.id,
            "session_id": row.session_id,
            "route": row.route,
            "title": row.title,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "chart_paths": json.loads(row.chart_paths or "[]"),
            "report_content": row.report_content or "",
        }
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
