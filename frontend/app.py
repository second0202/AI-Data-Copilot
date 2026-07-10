import json
import os

import pandas as pd
import requests
import streamlit as st

# Ensure data directory exists
os.makedirs("data", exist_ok=True)
os.makedirs(os.path.join("data", "charts"), exist_ok=True)

st.set_page_config(page_title="AI Data Copilot", page_icon=":bar_chart:", layout="wide")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(59,130,246,0.12), transparent 28%),
                    linear-gradient(180deg, #f8fbff 0%, #f4f7fb 100%);
            }
            .block-container {
                max-width: 1280px;
                padding-top: 1.35rem;
                padding-bottom: 2rem;
            }
            .hero-card {
                padding: 1.65rem 1.8rem;
                border-radius: 24px;
                color: #ffffff;
                background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 56%, #38bdf8 100%);
                box-shadow: 0 22px 52px rgba(15, 23, 42, 0.18);
                margin-bottom: 1rem;
            }
            .hero-title {
                font-size: 2rem;
                font-weight: 800;
                margin-bottom: 0.35rem;
            }
            .hero-subtitle {
                font-size: 1rem;
                line-height: 1.65;
                opacity: 0.92;
                max-width: 820px;
            }
            .hero-badges {
                margin-top: 1rem;
                display: flex;
                gap: 0.55rem;
                flex-wrap: wrap;
            }
            .hero-badge {
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.18);
                padding: 0.34rem 0.74rem;
                border-radius: 999px;
                font-size: 0.82rem;
            }
            .kpi-card {
                background: rgba(255,255,255,0.88);
                border: 1px solid rgba(148,163,184,0.18);
                border-radius: 18px;
                padding: 1rem 1.05rem;
                box-shadow: 0 10px 30px rgba(15,23,42,0.05);
                min-height: 118px;
                margin-bottom: 0.8rem;
            }
            .kpi-label {
                color: #64748b;
                font-size: 0.86rem;
                margin-bottom: 0.4rem;
            }
            .kpi-value {
                color: #0f172a;
                font-size: 1.72rem;
                font-weight: 800;
                margin-bottom: 0.28rem;
            }
            .kpi-help {
                color: #475569;
                font-size: 0.9rem;
                line-height: 1.45;
            }
            .soft-panel {
                background: rgba(255,255,255,0.86);
                border: 1px solid rgba(148,163,184,0.18);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                box-shadow: 0 12px 32px rgba(15,23,42,0.05);
                margin-bottom: 1rem;
            }
            .sidebar-card {
                background: rgba(255,255,255,0.72);
                border: 1px solid rgba(148,163,184,0.18);
                border-radius: 16px;
                padding: 0.9rem 1rem;
                margin-bottom: 0.85rem;
            }
            .section-title {
                font-size: 1.08rem;
                font-weight: 800;
                color: #0f172a;
                margin-bottom: 0.45rem;
            }
            .section-caption {
                color: #64748b;
                font-size: 0.9rem;
                line-height: 1.55;
                margin-bottom: 0.75rem;
            }
            .status-pill {
                display: inline-block;
                padding: 0.3rem 0.68rem;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 700;
                margin-right: 0.45rem;
                margin-bottom: 0.45rem;
            }
            .status-blue {
                color: #1d4ed8;
                background: rgba(59,130,246,0.12);
            }
            .status-slate {
                color: #334155;
                background: rgba(100,116,139,0.12);
            }
            .status-green {
                color: #047857;
                background: rgba(16,185,129,0.12);
            }
            .result-shell {
                background: rgba(255,255,255,0.92);
                border: 1px solid rgba(148,163,184,0.18);
                border-radius: 22px;
                padding: 1rem 1.15rem 0.75rem 1.15rem;
                box-shadow: 0 14px 34px rgba(15,23,42,0.05);
                margin-top: 1rem;
            }
            .small-muted {
                color: #64748b;
                font-size: 0.87rem;
            }
            .persona-card {
                background: rgba(255,255,255,0.9);
                border: 1px solid rgba(148,163,184,0.18);
                border-radius: 18px;
                padding: 1rem 1.1rem;
                box-shadow: 0 12px 30px rgba(15,23,42,0.05);
                margin-bottom: 1rem;
            }
            .persona-title {
                color: #0f172a;
                font-size: 1rem;
                font-weight: 800;
                margin-bottom: 0.35rem;
            }
            .persona-summary {
                color: #475569;
                font-size: 0.92rem;
                line-height: 1.6;
                margin-bottom: 0.75rem;
            }
            .persona-meta {
                color: #334155;
                font-size: 0.84rem;
                margin-bottom: 0.28rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(session_count: int, table_count: int, report_count: int) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-title">AI Data Copilot</div>
            <div class="hero-subtitle">
                多智能体数据分析工作台。支持多轮会话、结构化 SQL 预览、图表生成、历史报告归档与导出，
                更适合日常分析和演示场景。
            </div>
            <div class="hero-badges">
                <span class="hero-badge">会话 {session_count}</span>
                <span class="hero-badge">数据表 {table_count}</span>
                <span class="hero-badge">报告 {report_count}</span>
                <span class="hero-badge">Workflow Driven</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, help_text: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_persona_card(persona: dict) -> None:
    route_preferences = persona.get("route_preferences", {})
    default_route = route_preferences.get("default_route", "sql_only")
    prefer_chart = "是" if route_preferences.get("prefer_chart") else "否"
    prefer_python = "是" if route_preferences.get("prefer_python") else "否"
    st.markdown(
        f"""
        <div class="persona-card">
            <div class="persona-title">{persona.get("label", "")}</div>
            <div class="persona-summary">{persona.get("summary", "")}</div>
            <div class="persona-meta">默认路由倾向: <strong>{default_route}</strong></div>
            <div class="persona-meta">偏好图表链路: <strong>{prefer_chart}</strong></div>
            <div class="persona-meta">偏好 Python 分析: <strong>{prefer_python}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_tables(base_api_url: str) -> tuple[list[str], dict]:
    tables_url = base_api_url.replace("/analyze", "/datasets/tables")
    response = requests.get(tables_url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload.get("tables", []), payload.get("previews", {})


def get_sessions(base_api_url: str) -> list[str]:
    sessions_url = base_api_url.replace("/analyze", "/sessions")
    response = requests.get(sessions_url, timeout=30)
    response.raise_for_status()
    return response.json().get("sessions", [])


def get_session_detail(base_api_url: str, session_id: str) -> dict:
    session_url = base_api_url.replace("/analyze", f"/sessions/{session_id}")
    response = requests.get(session_url, timeout=30)
    response.raise_for_status()
    return response.json()


def get_reports(base_api_url: str, session_id: str | None = None) -> list[dict]:
    reports_url = base_api_url.replace("/analyze", "/reports")
    params = {"session_id": session_id} if session_id else None
    response = requests.get(reports_url, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("reports", [])


def get_personas(base_api_url: str) -> list[dict]:
    personas_url = base_api_url.replace("/analyze", "/personas")
    response = requests.get(personas_url, timeout=30)
    response.raise_for_status()
    return response.json().get("personas", [])


def get_report_detail(base_api_url: str, report_id: int) -> dict:
    report_url = base_api_url.replace("/analyze", f"/reports/{report_id}")
    response = requests.get(report_url, timeout=30)
    response.raise_for_status()
    return response.json()


def upload_dataset(base_api_url: str, uploaded_file) -> dict:
    upload_url = base_api_url.replace("/analyze", "/datasets/upload")
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }
    response = requests.post(upload_url, files=files, timeout=120)
    response.raise_for_status()
    return response.json()


def build_execution_log(structured_context: dict) -> list[dict]:
    sections = ["planner", "sql", "python", "chart", "report"]
    log_entries = []
    for section in sections:
        payload = structured_context.get(section)
        if payload:
            log_entries.append({"step": section, "details": payload})
    return log_entries


def format_api_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return response.text or "Unknown API error."

    detail = payload.get("detail", payload)
    if isinstance(detail, dict):
        return json.dumps(detail, ensure_ascii=False, indent=2)
    return str(detail)


def read_binary_file(file_path: str) -> bytes | None:
    if not file_path or not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as file:
        return file.read()


def dataframe_to_csv_bytes(rows: list[dict]) -> bytes | None:
    if not rows:
        return None
    dataframe = pd.DataFrame(rows)
    return dataframe.to_csv(index=False).encode("utf-8-sig")


def get_persona_label_from_options(persona_options: list[dict], persona_key: str) -> str:
    return next((item["label"] for item in persona_options if item["key"] == persona_key), persona_key)


def render_status_pills(route: str, session_id: str, report_id: int | None, persona_label: str | None = None) -> None:
    pills = [
        f'<span class="status-pill status-blue">Route: {route or "unknown"}</span>',
        f'<span class="status-pill status-slate">Session: {session_id or "new"}</span>',
    ]
    if persona_label:
        pills.append(f'<span class="status-pill status-slate">Persona: {persona_label}</span>')
    if report_id:
        pills.append(f'<span class="status-pill status-green">Report ID: {report_id}</span>')
    st.markdown("".join(pills), unsafe_allow_html=True)


def render_historical_reports(api_url: str, report_items: list[dict]) -> None:
    if not report_items:
        st.caption("当前会话还没有历史报告。")
        return

    report_search = st.text_input(
        "Search reports",
        value="",
        placeholder="Search by title, route, or preview",
    )
    filtered_report_items = [
        item
        for item in report_items
        if not report_search
        or report_search.lower() in item.get("title", "").lower()
        or report_search.lower() in item.get("route", "").lower()
        or report_search.lower() in item.get("report_preview", "").lower()
    ]
    if not filtered_report_items:
        st.info("No reports matched the current search.")
        filtered_report_items = report_items

    report_options = {
        f"{item['id']} | {item['title'][:42]} | {item['created_at']} | {item['route']}": item["id"]
        for item in filtered_report_items
    }
    selected_report_label = st.selectbox("Select a historical report", options=list(report_options.keys()))
    selected_report_id = report_options[selected_report_label]
    report_detail = get_report_detail(api_url, selected_report_id)

    st.markdown(f"### {report_detail['title']}")
    st.markdown(report_detail["report_content"])
    st.caption("Copy-friendly report block")
    st.code(report_detail["report_content"], language="markdown")
    st.download_button(
        label="Download Report",
        data=report_detail["report_content"],
        file_name=f"report_{report_detail['id']}.md",
        mime="text/markdown",
    )

    chart_paths = report_detail.get("chart_paths", [])
    if chart_paths:
        st.markdown("#### Archived Charts")
        for chart_path in chart_paths:
            chart_bytes = read_binary_file(chart_path)
            if chart_bytes:
                st.image(chart_path, caption=os.path.basename(chart_path))
                st.download_button(
                    label=f"Download {os.path.basename(chart_path)}",
                    data=chart_bytes,
                    file_name=os.path.basename(chart_path),
                    mime="image/png",
                    key=f"download-archived-chart-{report_detail['id']}-{chart_path}",
                )


def render_persona_examples(persona: dict) -> None:
    examples = persona.get("example_questions", [])
    if not examples:
        st.caption("当前 persona 暂无示例问题。")
        return

    st.markdown("#### 示例问题")
    example_columns = st.columns(1 if len(examples) == 1 else min(2, len(examples)))
    for idx, example in enumerate(examples):
        with example_columns[idx % len(example_columns)]:
            if st.button(example, key=f"persona-example-{persona.get('key', 'default')}-{idx}", use_container_width=True):
                st.session_state["prefill_query"] = example
                st.session_state["query_input"] = example


def render_analysis_result(data: dict) -> None:
    st.markdown('<div class="result-shell">', unsafe_allow_html=True)
    render_status_pills(
        data.get("route", ""),
        data.get("session_id", ""),
        data.get("report_id"),
        data.get("agent_persona_label"),
    )
    if data.get("error"):
        st.warning(f"Execution warning: {data['error']}")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ["Final Report", "Plan", "SQL Generated", "Python Code", "Charts", "Execution Context", "Execution Log"]
    )

    with tab1:
        st.markdown("### Analysis Report")
        st.markdown(data.get("final_report", "No report generated."))
        download_col1, download_col2 = st.columns(2)
        with download_col1:
            st.download_button(
                label="Download Current Report",
                data=data.get("final_report", ""),
                file_name=f"report_{data.get('report_id', 'latest')}.md",
                mime="text/markdown",
            )
        with download_col2:
            st.download_button(
                label="Download Report as TXT",
                data=data.get("final_report", ""),
                file_name=f"report_{data.get('report_id', 'latest')}.txt",
                mime="text/plain",
            )
        st.caption("Copy-friendly report block")
        st.code(data.get("final_report", ""), language="markdown")

    with tab2:
        st.markdown("### Execution Plan")
        st.markdown(data.get("plan", ""))

    with tab3:
        st.markdown("### SQL Query")
        st.code(data.get("sql_query", ""), language="sql")
        st.download_button(
            label="Download SQL",
            data=data.get("sql_query", ""),
            file_name=f"query_{data.get('report_id', 'latest')}.sql",
            mime="text/sql",
        )
        sql_preview = data.get("sql_preview_data", {"columns": [], "rows": []})
        preview_rows = sql_preview.get("rows", [])
        if preview_rows:
            st.markdown("### SQL Result Preview")
            preview_df = pd.DataFrame(preview_rows)
            st.dataframe(preview_df, use_container_width=True)
            csv_bytes = dataframe_to_csv_bytes(preview_rows)
            if csv_bytes:
                st.download_button(
                    label="Download SQL Result as CSV",
                    data=csv_bytes,
                    file_name=f"sql_result_{data.get('report_id', 'latest')}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No structured SQL preview data available for this request.")

    with tab4:
        st.markdown("### Python Analysis Code")
        st.code(data.get("python_code", ""), language="python")

    with tab5:
        st.markdown("### Generated Charts")
        chart_paths = data.get("chart_paths", [])
        if not chart_paths:
            st.info("No charts were generated for this request.")
        else:
            for chart_path in chart_paths:
                if chart_path.startswith("图表生成失败") or chart_path.startswith("Error generating chart:"):
                    st.error(chart_path)
                else:
                    chart_bytes = read_binary_file(chart_path)
                    st.image(chart_path, caption=os.path.basename(chart_path))
                    if chart_bytes:
                        st.download_button(
                            label=f"Download {os.path.basename(chart_path)}",
                            data=chart_bytes,
                            file_name=os.path.basename(chart_path),
                            mime="image/png",
                            key=f"download-current-chart-{chart_path}",
                        )

    with tab6:
        st.markdown("### Structured Context")
        st.json(data.get("structured_context", {}))

    with tab7:
        st.markdown("### Execution Log")
        log_entries = build_execution_log(data.get("structured_context", {}))
        if not log_entries:
            st.info("No execution log available.")
        else:
            for entry in log_entries:
                with st.expander(entry["step"], expanded=True):
                    st.json(entry["details"])

    st.markdown("</div>", unsafe_allow_html=True)


inject_styles()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = ""
if "latest_analysis" not in st.session_state:
    st.session_state["latest_analysis"] = None
if "selected_persona" not in st.session_state:
    st.session_state["selected_persona"] = "data_analyst"
if "prefill_query" not in st.session_state:
    st.session_state["prefill_query"] = ""
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""

# Sidebar for configuration
with st.sidebar:
    st.markdown(
        '<div class="sidebar-card"><strong>Workspace Settings</strong><div class="small-muted">配置接口、会话与数据集入口。</div></div>',
        unsafe_allow_html=True,
    )

    api_url = st.text_input("Backend API URL", value="http://localhost:8000/api/v1/analyze")
    personas = []
    try:
        personas = get_personas(api_url)
    except Exception as exc:
        st.caption(f"Persona metadata unavailable: {exc}")

    session_options = []
    try:
        session_options = get_sessions(api_url)
    except Exception as exc:
        st.caption(f"Session metadata unavailable: {exc}")

    st.markdown("### Session")
    new_session = st.button("New Session")
    if new_session:
        st.session_state["session_id"] = ""
        st.session_state["latest_analysis"] = None

    session_selector_options = [""] + session_options
    current_session = st.session_state.get("session_id", "")
    current_index = session_selector_options.index(current_session) if current_session in session_selector_options else 0
    selected_session = st.selectbox(
        "Select session",
        options=session_selector_options,
        index=current_index,
        format_func=lambda value: value or "Create new session",
    )
    if selected_session != st.session_state.get("session_id", ""):
        st.session_state["session_id"] = selected_session
        st.session_state["latest_analysis"] = None

    st.markdown("### Agent Persona")
    persona_options = personas or [
        {"key": "data_analyst", "label": "数据分析师", "summary": "通用数据分析与业务结论总结。"},
        {"key": "sql_expert", "label": "SQL 专家", "summary": "复杂 SQL 与高质量查询生成。"},
        {"key": "python_analyst", "label": "Python 分析师", "summary": "统计分析与深度模式识别。"},
        {"key": "visualization_expert", "label": "图表可视化专家", "summary": "图表设计与可视化表达。"},
        {"key": "executive_briefing", "label": "决策汇报专家", "summary": "面向管理层的结论与行动建议。"},
    ]
    persona_keys = [item["key"] for item in persona_options]
    current_persona = st.session_state.get("selected_persona", "data_analyst")
    persona_index = persona_keys.index(current_persona) if current_persona in persona_keys else 0
    selected_persona = st.selectbox(
        "Select persona",
        options=persona_keys,
        index=persona_index,
        format_func=lambda key: next((item["label"] for item in persona_options if item["key"] == key), key),
    )
    st.session_state["selected_persona"] = selected_persona
    selected_persona_summary = next((item["summary"] for item in persona_options if item["key"] == selected_persona), "")
    st.caption(selected_persona_summary)

    tables = []
    previews = {}
    try:
        tables, previews = get_tables(api_url)
    except Exception as exc:
        st.caption(f"Table metadata unavailable: {exc}")

    st.markdown("### Dataset Upload")
    uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx"])
    if uploaded_file is not None and st.button("Upload Dataset"):
        try:
            payload = upload_dataset(api_url, uploaded_file)
            st.success(f"Uploaded to table `{payload['table_name']}` with {payload['row_count']} rows.")
            tables, previews = get_tables(api_url)
        except Exception as exc:
            st.error(f"Upload failed: {exc}")

    if tables:
        st.markdown("### Available Tables")
        selected_tables = st.multiselect("Select tables to focus on", tables, default=tables[:1])
        for table_name in selected_tables:
            preview_rows = previews.get(table_name, [])
            if preview_rows:
                st.caption(f"Preview: {table_name}")
                st.dataframe(preview_rows, use_container_width=True)
    else:
        selected_tables = []

    st.markdown("### Sample Data")
    if st.button("Initialize Sample Database"):
        import duckdb

        conn = duckdb.connect("data/analytics.duckdb")
        conn.execute("CREATE TABLE IF NOT EXISTS sales (id INTEGER, product VARCHAR, amount DOUBLE, date DATE)")
        conn.execute("DELETE FROM sales")
        conn.execute("INSERT INTO sales VALUES (1, 'Laptop', 1200.50, '2023-01-15'), (2, 'Mouse', 25.00, '2023-01-16'), (3, 'Keyboard', 45.00, '2023-01-17')")
        conn.close()
        st.success("Sample data initialized!")

session_payload = {}
report_items = []
history = []
if st.session_state.get("session_id"):
    try:
        session_payload = get_session_detail(api_url, st.session_state["session_id"])
        report_items = get_reports(api_url, st.session_state["session_id"])
        history = session_payload.get("history", [])
    except Exception as exc:
        st.warning(f"Failed to load session history: {exc}")

all_reports = []
try:
    all_reports = get_reports(api_url)
except Exception:
    all_reports = []

render_hero(len(session_options), len(tables), len(all_reports))

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
with kpi_col1:
    render_kpi_card("当前会话", st.session_state.get("session_id", "") or "New", "保持同一会话可启用多轮上下文。")
with kpi_col2:
    render_kpi_card("可用数据表", str(len(tables)), "支持上传 CSV/XLSX 并自动接入 DuckDB。")
with kpi_col3:
    render_kpi_card("聚焦数据表", str(len(selected_tables)), "Planner 会优先参考你选中的数据表。")
with kpi_col4:
    latest_persona = st.session_state.get("selected_persona", "data_analyst")
    latest_persona_label = get_persona_label_from_options(persona_options, latest_persona)
    render_kpi_card("当前角色", latest_persona_label, "已支持方案A的5类专用 Agent 人设。")

main_col, side_col = st.columns([1.6, 0.95])

with main_col:
    st.markdown('<div class="soft-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Analysis Workspace</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">输入一个分析任务，系统会自动生成执行计划，并在需要时完成 SQL、Python 与图表协作。你也可以切换专用 Agent 人设来改变输出风格与策略。</div>',
        unsafe_allow_html=True,
    )

    selected_persona_config = next((item for item in persona_options if item["key"] == st.session_state.get("selected_persona")), {})
    render_persona_card(selected_persona_config)
    render_persona_examples(selected_persona_config)

    query = st.text_area(
        "What would you like to analyze?",
        height=130,
        placeholder="例如：分析 sales 表的销售趋势，并生成一份适合周会汇报的总结。",
        label_visibility="collapsed",
        value=st.session_state.get("prefill_query", ""),
        key="query_input",
    )

    action_col1, action_col2 = st.columns([0.18, 0.82])
    analyze_clicked = action_col1.button("Analyze", type="primary", use_container_width=True)
    action_col2.markdown(
        '<div class="small-muted" style="padding-top:0.55rem;">支持多轮上下文、结构化 SQL 预览、图表下载、历史报告归档，以及 persona 专属路由偏好。</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with side_col:
    st.markdown('<div class="soft-panel">', unsafe_allow_html=True)
    st.markdown("#### Session Overview")
    st.caption("查看当前工作状态、会话信息和聚焦表。")
    st.write(f"Session ID: `{st.session_state.get('session_id') or '未创建'}`")
    st.write(f"Historical reports: `{len(report_items)}`")
    st.write(f"Focused tables: `{', '.join(selected_tables) if selected_tables else 'None'}`")
    st.markdown("</div>", unsafe_allow_html=True)

    if history:
        with st.expander("Conversation History", expanded=False):
            for item in history:
                st.markdown(f"**{item['role']}**: {item['content']}")

    with st.expander("Historical Reports", expanded=False):
        render_historical_reports(api_url, report_items)

if analyze_clicked:
    if not query:
        st.warning("Please enter a query.")
    else:
        with st.spinner("Agents are working on your request..."):
            try:
                final_query = query
                if selected_tables:
                    final_query = f"{query}\n\nFocus on these tables first: {', '.join(selected_tables)}"

                response = requests.post(
                    api_url,
                    json={
                        "query": final_query,
                        "session_id": st.session_state.get("session_id") or None,
                        "agent_persona": st.session_state.get("selected_persona", "data_analyst"),
                    },
                    timeout=180,
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state["session_id"] = data.get("session_id", "")
                    st.session_state["report_id"] = data.get("report_id")
                    st.session_state["latest_analysis"] = data
                    st.session_state["prefill_query"] = query
                else:
                    st.error(f"Error from API: {format_api_error(response)}")
            except Exception as exc:
                st.error(f"Connection Error: {str(exc)}")

latest_analysis = st.session_state.get("latest_analysis")
if latest_analysis:
    render_analysis_result(latest_analysis)
else:
    st.markdown(
        """
        <div class="soft-panel">
            <div class="section-title">Ready To Analyze</div>
            <div class="section-caption">
                先在左侧选择或上传数据，再在上方输入分析问题。分析完成后，这里会展示报告、SQL 结果、图表和执行日志。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
