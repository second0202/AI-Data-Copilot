import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from core.workflow.state import AgentState
from config.prompts import (
    CHART_AGENT_PROMPT,
    PLANNER_PROMPT,
    PYTHON_AGENT_PROMPT,
    REPORT_AGENT_PROMPT,
    SQL_AGENT_PROMPT,
    build_persona_prompt,
    get_persona_examples,
    get_persona_label,
    get_persona_route_preferences,
)
from core.tools.tools import draw_chart, execute_sql, get_database_schema, run_python
from config.settings import settings

VALID_ROUTES = {"direct", "sql_only", "sql_python", "sql_chart", "sql_python_chart"}

# Initialize LLM
llm = ChatOpenAI(model=settings.MODEL_NAME, temperature=0, openai_api_key=settings.OPENAI_API_KEY)


def _clean_code_block(text: str, language: str = "") -> str:
    cleaned = text.strip()
    if language:
        cleaned = cleaned.replace(f"```{language}", "")
    return cleaned.replace("```", "").strip()


def _route_from_query(user_query: str, persona_key: str = "data_analyst") -> str:
    query = user_query.lower()
    route_preferences = get_persona_route_preferences(persona_key)
    chart_keywords = [
        "chart", "plot", "visual", "graph", "trend", "图", "图表", "可视化", *route_preferences.get("chart_keywords", [])
    ]
    python_keywords = [
        "forecast", "predict", "correlation", "regression", "统计", "分析", "分组", "同比", "环比",
        *route_preferences.get("python_keywords", []),
    ]
    direct_keywords = ["hello", "hi", "help", "你是谁", "你能做什么", "介绍一下", *route_preferences.get("direct_keywords", [])]

    if any(keyword in query for keyword in direct_keywords):
        return "direct"

    needs_chart = any(keyword in query for keyword in chart_keywords)
    needs_python = any(keyword in query for keyword in python_keywords)

    if route_preferences.get("prefer_chart") and any(keyword in query for keyword in ["汇报", "展示", "看板", "趋势", "图"]):
        needs_chart = True
    if route_preferences.get("prefer_python") and any(keyword in query for keyword in ["归因", "模式", "洞察", "细分", "预测", "分析"]):
        needs_python = True

    if needs_chart and needs_python:
        return "sql_python_chart"
    if needs_chart:
        return "sql_chart"
    if needs_python:
        return "sql_python"
    return route_preferences.get("default_route", "sql_only")


def _parse_planner_response(raw_text: str, user_query: str, persona_key: str) -> tuple[str, str]:
    try:
        data = json.loads(raw_text)
        route = data.get("route", "").strip()
        plan = data.get("plan", "").strip()
        if route in VALID_ROUTES and plan:
            return route, plan
    except Exception:
        pass

    route = _route_from_query(user_query, persona_key)
    examples = get_persona_examples(persona_key)
    example_hint = f" Persona examples: {' | '.join(examples[:2])}" if examples else ""
    return route, f"Fallback route selected for persona {get_persona_label(persona_key)}: {route}.{example_hint}"


def _merge_context(state: AgentState, section: str, payload: dict) -> dict:
    structured_context = dict(state.get("structured_context", {}))
    existing_section = structured_context.get(section, {})
    if isinstance(existing_section, dict):
        merged_section = {**existing_section, **payload}
    else:
        merged_section = payload
    structured_context[section] = merged_section
    return structured_context


def _append_log(state: AgentState, step: str, details: dict) -> dict:
    structured_context = dict(state.get("structured_context", {}))
    execution_log = list(structured_context.get("execution_log", []))
    execution_log.append({"step": step, "details": details})
    structured_context["execution_log"] = execution_log
    return structured_context


def _get_session_context(state: AgentState) -> str:
    session_history_text = state.get("session_history_text", "").strip()
    session_context = state.get("structured_context", {}).get("session", {})
    latest_state = session_context.get("latest_state", {})
    latest_report = latest_state.get("report", {}).get("final_report", "")

    context_parts = [f"Recent Conversation History:\n{session_history_text or 'No prior conversation history.'}"]
    if latest_report:
        context_parts.append(f"Latest Session Report Summary:\n{latest_report}")
    return "\n\n".join(context_parts)


def _get_persona_context(state: AgentState, stage: str) -> str:
    persona_key = state.get("agent_persona", "data_analyst")
    return build_persona_prompt(persona_key, stage)


def planner_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    user_query = messages[0].content if messages else ""
    schema = get_database_schema()
    session_context = _get_session_context(state)
    persona_key = state.get("agent_persona", "data_analyst")
    persona_context = _get_persona_context(state, "planner")
    sys_msg = SystemMessage(content=PLANNER_PROMPT + f"\n\n{persona_context}\n\nDatabase Schema:\n{schema}\n\n{session_context}")
    response = llm.invoke([sys_msg, HumanMessage(content=user_query)])
    route, plan = _parse_planner_response(response.content, user_query, persona_key)
    structured_context = _merge_context(
        state,
        "planner",
        {
            "route": route,
            "plan": plan,
            "user_query": user_query,
            "session_context_used": session_context,
            "agent_persona": persona_key,
            "agent_persona_label": get_persona_label(persona_key),
        },
    )
    temp_state = dict(state)
    temp_state["structured_context"] = structured_context
    structured_context = _append_log(
        temp_state,
        "planner",
        {"route": route, "plan": plan, "user_query": user_query, "agent_persona": get_persona_label(persona_key)},
    )
    return {"plan": plan, "route": route, "structured_context": structured_context, "current_agent": "planner"}


def direct_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    user_query = messages[0].content if messages else ""
    session_context = _get_session_context(state)
    persona_context = _get_persona_context(state, "direct")
    sys_msg = SystemMessage(
        content="You are a helpful analytics copilot. Answer directly and concisely.\n\n" + persona_context + "\n\n" + session_context
    )
    response = llm.invoke([sys_msg, HumanMessage(content=user_query)])
    structured_context = _merge_context(state, "direct", {"response": response.content})
    temp_state = dict(state)
    temp_state["structured_context"] = structured_context
    structured_context = _append_log(temp_state, "direct", {"response": response.content})
    return {"final_report": response.content, "structured_context": structured_context, "current_agent": "end"}


def sql_node(state: AgentState) -> dict:
    plan = state.get("plan", "")
    schema = get_database_schema()
    session_context = _get_session_context(state)
    persona_context = _get_persona_context(state, "sql")
    sys_msg = SystemMessage(content=SQL_AGENT_PROMPT + f"\n\n{persona_context}\n\nDatabase Schema:\n{schema}\n\nPlan: {plan}\n\n{session_context}")
    user_msg = HumanMessage(content="Generate the SQL query based on the plan. Output ONLY the raw SQL query, no markdown blocks.")
    response = llm.invoke([sys_msg, user_msg])
    sql_query = _clean_code_block(response.content, "sql")
    sql_result = execute_sql(sql_query)
    structured_context = _merge_context(
        state,
        "sql",
        {
            "query": sql_query,
            "success": sql_result["success"],
            "row_count": sql_result.get("row_count", 0),
            "truncated": sql_result.get("truncated", False),
            "preview": sql_result["output"],
            "preview_data": sql_result.get("preview_data", {"columns": [], "rows": []}),
            "error": sql_result["error"],
        },
    )
    temp_state = dict(state)
    temp_state["structured_context"] = structured_context
    structured_context = _append_log(
        temp_state,
        "sql",
        {
            "query": sql_query,
            "success": sql_result["success"],
            "row_count": sql_result.get("row_count", 0),
            "error": sql_result["error"],
        },
    )
    return {
        "sql_query": sql_query,
        "sql_preview_data": sql_result.get("preview_data", {"columns": [], "rows": []}),
        "data_context": sql_result["output"] if sql_result["success"] else sql_result["error"],
        "error": sql_result["error"],
        "structured_context": structured_context,
        "current_agent": "sql_agent",
    }


def python_node(state: AgentState) -> dict:
    data_context = state.get("data_context", "")
    plan = state.get("plan", "")
    session_context = _get_session_context(state)
    persona_context = _get_persona_context(state, "python")
    sys_msg = SystemMessage(
        content=PYTHON_AGENT_PROMPT + f"\n\n{persona_context}\n\nData Context:\n{data_context}\n\nPlan: {plan}\n\n{session_context}"
    )
    user_msg = HumanMessage(content="Generate Python code to analyze this data. Output ONLY the raw python code, no markdown.")
    response = llm.invoke([sys_msg, user_msg])
    python_code = _clean_code_block(response.content, "python")
    python_result = run_python(python_code)
    analysis_text = python_result["output"] if python_result["success"] else python_result["error"]
    structured_context = _merge_context(
        state,
        "python",
        {
            "code": python_code,
            "success": python_result["success"],
            "output": python_result["output"],
            "error": python_result["error"],
        },
    )
    temp_state = dict(state)
    temp_state["structured_context"] = structured_context
    structured_context = _append_log(
        temp_state,
        "python",
        {
            "success": python_result["success"],
            "output": python_result["output"],
            "error": python_result["error"],
        },
    )
    return {
        "python_code": python_code,
        "data_context": data_context + "\n\nAnalysis Result:\n" + analysis_text,
        "error": python_result["error"],
        "structured_context": structured_context,
        "current_agent": "python_agent",
    }


def chart_node(state: AgentState) -> dict:
    data_context = state.get("data_context", "")
    plan = state.get("plan", "")
    session_context = _get_session_context(state)
    persona_context = _get_persona_context(state, "chart")
    sys_msg = SystemMessage(
        content=CHART_AGENT_PROMPT + f"\n\n{persona_context}\n\nData Context:\n{data_context}\n\nPlan: {plan}\n\n{session_context}"
    )
    user_msg = HumanMessage(
        content=(
            "Generate Python code to produce the most useful chart for this request. "
            "Save chart images and set a chart_paths list variable. Output only raw python code."
        )
    )
    response = llm.invoke([sys_msg, user_msg])
    chart_code = _clean_code_block(response.content, "python")
    chart_result = draw_chart(chart_code)
    chart_paths = chart_result["chart_paths"]
    chart_note = "Charts: " + (", ".join(chart_paths) if chart_paths else "none")
    if chart_result["error"]:
        chart_note += f"\nChart Error: {chart_result['error']}"
    structured_context = _merge_context(
        state,
        "chart",
        {
            "code": chart_code,
            "success": chart_result["success"],
            "chart_paths": chart_paths,
            "error": chart_result["error"],
        },
    )
    temp_state = dict(state)
    temp_state["structured_context"] = structured_context
    structured_context = _append_log(
        temp_state,
        "chart",
        {
            "success": chart_result["success"],
            "chart_paths": chart_paths,
            "error": chart_result["error"],
        },
    )
    return {
        "chart_code": chart_code,
        "chart_paths": chart_paths,
        "data_context": data_context + "\n\n" + chart_note,
        "error": chart_result["error"],
        "structured_context": structured_context,
        "current_agent": "chart_agent",
    }


def report_node(state: AgentState) -> dict:
    plan = state.get("plan", "")
    data_context = state.get("data_context", "")
    chart_paths = state.get("chart_paths", [])
    error = state.get("error", "")
    session_context = _get_session_context(state)
    persona_context = _get_persona_context(state, "report")
    sys_msg = SystemMessage(content=REPORT_AGENT_PROMPT + f"\n\n{persona_context}")
    user_msg = HumanMessage(
        content=(
            f"Plan: {plan}\n\n"
            f"Data & Analysis:\n{data_context}\n\n"
            f"Chart Paths: {chart_paths}\n\n"
            f"Execution Error: {error}\n\n"
            f"{session_context}\n\n"
            "Please write the final report."
        )
    )
    response = llm.invoke([sys_msg, user_msg])
    structured_context = _merge_context(
        state,
        "report",
        {"final_report": response.content, "error": error, "chart_paths": chart_paths},
    )
    temp_state = dict(state)
    temp_state["structured_context"] = structured_context
    structured_context = _append_log(
        temp_state,
        "report",
        {"final_report": response.content, "error": error, "chart_paths": chart_paths},
    )
    return {"final_report": response.content, "error": error, "structured_context": structured_context, "current_agent": "end"}
