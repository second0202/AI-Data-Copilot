import io
import contextlib
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import matplotlib.pyplot as plt
import pandas as pd

from core.data_connectors.duckdb_connector import duckdb_connector

_LAST_QUERY_DF = pd.DataFrame()
MAX_SQL_ROWS = 5000
EXECUTION_TIMEOUT_SECONDS = 8
FORBIDDEN_SQL_PATTERNS = [
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\btruncate\b",
    r"\bcreate\b",
    r"\battach\b",
    r"\bcopy\b",
]
SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}
FORBIDDEN_PYTHON_PATTERNS = [
    r"__import__",
    r"\bimport\s+os\b",
    r"\bimport\s+sys\b",
    r"\bimport\s+subprocess\b",
    r"\bfrom\s+os\b",
    r"\bfrom\s+sys\b",
    r"\bfrom\s+subprocess\b",
    r"\bopen\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
]


def _format_dataframe(df: pd.DataFrame, max_rows: int = 10) -> str:
    if df.empty:
        return "Query succeeded but returned no rows."
    preview = df.head(max_rows).to_string(index=False)
    return f"Rows: {len(df)}\nColumns: {', '.join(df.columns.tolist())}\nPreview:\n{preview}"


def _dataframe_preview(df: pd.DataFrame, max_rows: int = 50) -> dict:
    safe_df = df.head(max_rows).copy()
    safe_df = safe_df.where(pd.notnull(safe_df), None)
    return {
        "columns": safe_df.columns.tolist(),
        "rows": safe_df.to_dict(orient="records"),
    }


def _humanize_sql_error(error_message: str) -> str:
    lowered = error_message.lower()
    if "catalog error" in lowered and "does not exist" in lowered:
        return "SQL 执行失败：引用的数据表不存在，请检查表名是否正确，或先在侧边栏确认可用表。"
    if "binder error" in lowered and "referenced column" in lowered:
        return "SQL 执行失败：引用的字段不存在，请检查字段名是否正确。"
    if "parser error" in lowered or "syntax error" in lowered:
        return "SQL 执行失败：生成的 SQL 语法不正确，需要重新调整查询。"
    if "only read-only" in lowered:
        return "SQL 执行被拦截：当前系统只允许只读查询，不允许修改数据库。"
    if "empty" in lowered and "sql query" in lowered:
        return "SQL 执行失败：没有生成有效的查询语句。"
    return f"SQL 执行失败：{error_message}"


def _humanize_python_error(error_message: str) -> str:
    lowered = error_message.lower()
    if "timed out" in lowered:
        return "Python 分析超时：分析代码运行时间过长，请缩小数据范围或简化分析任务。"
    if "blocked unsafe python pattern" in lowered:
        return "Python 分析被拦截：生成的代码包含受限操作，系统已阻止执行。"
    if "nameerror" in lowered:
        return "Python 分析失败：代码引用了未定义变量，通常是模型生成代码不完整导致。"
    if "keyerror" in lowered:
        return "Python 分析失败：代码访问了不存在的列，请检查字段名。"
    if "valueerror" in lowered:
        return "Python 分析失败：输入值或数据格式不符合预期。"
    return f"Python 分析失败：{error_message}"


def _humanize_chart_error(error_message: str) -> str:
    lowered = error_message.lower()
    if "timed out" in lowered:
        return "图表生成超时：绘图过程耗时过长，请缩小数据范围后重试。"
    if "blocked unsafe python pattern" in lowered:
        return "图表生成被拦截：绘图代码包含受限操作，系统已阻止执行。"
    if "no such file" in lowered:
        return "图表生成失败：目标文件路径无效。"
    return f"图表生成失败：{error_message}"


def _normalize_query(query: str) -> str:
    return query.strip().rstrip(";")


def _validate_sql(query: str) -> tuple[bool, str]:
    normalized = _normalize_query(query).lower()
    if not normalized:
        return False, "SQL query is empty."
    if not normalized.startswith(("select", "with", "show", "describe")):
        return False, "Only read-only SELECT/WITH/SHOW/DESCRIBE queries are allowed."
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, normalized):
            return False, f"Blocked unsafe SQL pattern: {pattern}"
    return True, ""


def execute_sql(query: str) -> dict:
    """Execute a read-only SQL query against DuckDB."""
    global _LAST_QUERY_DF
    is_valid, validation_message = _validate_sql(query)
    if not is_valid:
        _LAST_QUERY_DF = pd.DataFrame()
        return {
            "success": False,
            "output": "",
            "error": _humanize_sql_error(validation_message),
            "row_count": 0,
            "truncated": False,
            "preview_data": {"columns": [], "rows": []},
        }

    try:
        df = duckdb_connector.execute_query(_normalize_query(query))
        row_count = len(df)
        truncated = row_count > MAX_SQL_ROWS
        safe_df = df.head(MAX_SQL_ROWS).copy() if truncated else df.copy()
        _LAST_QUERY_DF = safe_df
        output = _format_dataframe(safe_df)
        if truncated:
            output += f"\n\nResult truncated to first {MAX_SQL_ROWS} rows for safety."
        return {
            "success": True,
            "output": output,
            "error": "",
            "row_count": row_count,
            "truncated": truncated,
            "preview_data": _dataframe_preview(safe_df),
        }
    except Exception as e:
        _LAST_QUERY_DF = pd.DataFrame()
        return {
            "success": False,
            "output": "",
            "error": _humanize_sql_error(str(e)),
            "row_count": 0,
            "truncated": False,
            "preview_data": {"columns": [], "rows": []},
        }


def _validate_python_code(code: str) -> tuple[bool, str]:
    for pattern in FORBIDDEN_PYTHON_PATTERNS:
        if re.search(pattern, code):
            return False, f"Blocked unsafe Python pattern: {pattern}"
    return True, ""


def _execute_python(code: str, local_vars: dict) -> str:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(code, {"__builtins__": SAFE_BUILTINS}, local_vars)
    return output.getvalue().strip() or "Python execution completed."


def run_python(code: str) -> dict:
    """Execute Python code in a restricted environment and return the standard output."""
    is_valid, validation_message = _validate_python_code(code)
    if not is_valid:
        return {"success": False, "output": "", "error": _humanize_python_error(validation_message)}

    local_vars = {"df": _LAST_QUERY_DF.copy(), "pd": pd}
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_execute_python, code, local_vars)
            output = future.result(timeout=EXECUTION_TIMEOUT_SECONDS)
        return {"success": True, "output": output, "error": ""}
    except FuturesTimeoutError:
        return {"success": False, "output": "", "error": _humanize_python_error(f"timed out after {EXECUTION_TIMEOUT_SECONDS} seconds")}
    except Exception as e:
        return {"success": False, "output": "", "error": _humanize_python_error(str(e))}


def draw_chart(code: str) -> dict:
    """Execute chart code in a restricted environment and return saved chart file paths."""
    is_valid, validation_message = _validate_python_code(code)
    if not is_valid:
        return {"success": False, "chart_paths": [], "error": _humanize_chart_error(validation_message)}

    plt.switch_backend("Agg")
    charts_dir = os.path.join("data", "charts")
    os.makedirs(charts_dir, exist_ok=True)
    local_vars = {
        "df": _LAST_QUERY_DF.copy(),
        "pd": pd,
        "plt": plt,
        "os": os,
        "charts_dir": charts_dir,
        "timestamp": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "chart_paths": [],
    }
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_execute_python, code, local_vars)
            future.result(timeout=EXECUTION_TIMEOUT_SECONDS)
        chart_paths = local_vars.get("chart_paths", [])
        if isinstance(chart_paths, str):
            chart_paths = [chart_paths]
        return {
            "success": True,
            "chart_paths": [path for path in chart_paths if path],
            "error": "",
        }
    except FuturesTimeoutError:
        return {
            "success": False,
            "chart_paths": [],
            "error": _humanize_chart_error(f"timed out after {EXECUTION_TIMEOUT_SECONDS} seconds"),
        }
    except Exception as e:
        return {
            "success": False,
            "chart_paths": [],
            "error": _humanize_chart_error(str(e)),
        }


def get_database_schema() -> str:
    """Get the current database schema."""
    return duckdb_connector.get_schema()
