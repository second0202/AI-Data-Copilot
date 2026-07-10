from typing import TypedDict, List, Annotated, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], operator.add]
    current_agent: str
    agent_persona: str
    plan: str
    route: str
    session_history_text: str
    data_context: str
    structured_context: Dict[str, Any]
    sql_query: str
    sql_preview_data: Dict[str, Any]
    python_code: str
    chart_code: str
    chart_paths: List[str]
    final_report: str
    error: str
