from langgraph.graph import StateGraph, END
from core.workflow.state import AgentState
from core.agents.nodes import chart_node, direct_node, planner_node, python_node, report_node, sql_node


def route_from_planner(state: AgentState) -> str:
    return state.get("route", "sql_only")


def route_after_sql(state: AgentState) -> str:
    if state.get("error"):
        return "report"
    route = state.get("route", "sql_only")
    if route == "sql_only":
        return "report"
    if route == "sql_python":
        return "python"
    if route == "sql_chart":
        return "chart"
    return "python"


def route_after_python(state: AgentState) -> str:
    if state.get("error"):
        return "report"
    route = state.get("route", "sql_python")
    if route == "sql_python_chart":
        return "chart"
    return "report"

def build_graph():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("direct", direct_node)
    workflow.add_node("sql", sql_node)
    workflow.add_node("python", python_node)
    workflow.add_node("chart", chart_node)
    workflow.add_node("report", report_node)

    # Define edges
    workflow.set_entry_point("planner")
    workflow.add_conditional_edges(
        "planner",
        route_from_planner,
        {
            "direct": "direct",
            "sql_only": "sql",
            "sql_python": "sql",
            "sql_chart": "sql",
            "sql_python_chart": "sql",
        },
    )
    workflow.add_conditional_edges(
        "sql",
        route_after_sql,
        {"python": "python", "chart": "chart", "report": "report"},
    )
    workflow.add_conditional_edges(
        "python",
        route_after_python,
        {"chart": "chart", "report": "report"},
    )
    workflow.add_edge("direct", END)
    workflow.add_edge("chart", "report")
    workflow.add_edge("report", END)

    # Compile
    app = workflow.compile()
    return app

workflow_app = build_graph()
