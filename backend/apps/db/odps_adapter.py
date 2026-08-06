"""
ODPS Adapter — 通过 SSH 远程调用 odpscmd，返回结构化查询结果。

复用 ODPS MCP 背后的链路：
  SSH -> zabank-sit-dws-dataide-service-04002 -> odpscmd -> zabank_dw

只读安全：仅允许 SELECT / SHOW / DESC / DESCRIBE / EXPLAIN。
"""

import subprocess
import re
import os
import sys
from typing import Any
from dataclasses import dataclass, field


# ── Config ──────────────────────────────────────────────

SSH_HOST = "zabank-sit-dws-dataide-service-04002"
ODPSCMD_PATH = "/home/za_schedule/odps/odpscmd/bin/odpscmd"
CONFIG_PREFIX = "/home/za_schedule/odps/ide_config/5530414855159702_shaojie.jiang"

PROJECT_MAP = {
    "zabank_dw": "zabank_dw_sit",
    "zabank_dw_dev": "zabank_dw_dev",
    "zabank_dw_sit": "zabank_dw_sit",
    "za_zebra_dev": "za_zebra_dev",
    "zhongan": "zhongan",
}

ENV_MAP = {
    "prd": "prd",
    "test": "test",
    "dev": "dev",
}

# Windows OpenSSH (avoid Git Bash SSH conflicts / MAC errors)
SSH_CMD = (
    r"C:\Windows\System32\OpenSSH\ssh.exe"
    if sys.platform == "win32"
    else "ssh"
)

# Read-only SQL whitelist
READONLY_PREFIXES = ("SELECT", "SHOW", "DESC", "DESCRIBE", "EXPLAIN")
FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "MSCK", "ADD", "OVERWRITE", "GRANT", "REVOKE",
)

# Noise lines to strip from odpscmd output
NOISE_PREFIXES = (
    "Authorized", "ID =", "Session", "******", "Odps",
    "Warning:", "OK", "Summary:", "RunTime:",
)


# ── Result Types ────────────────────────────────────────

@dataclass
class OdpsQueryResult:
    columns: list[dict[str, str]] = field(default_factory=list)  # [{name, type}]
    rows: list[dict[str, Any]] = field(default_factory=list)
    raw_output: str = ""
    logview_url: str | None = None
    duration_ms: int = 0
    status: str = "success"  # success / error
    error_message: str | None = None


# ── Config Path Builder ─────────────────────────────────

def get_config_path(project: str, env: str = "prd") -> str:
    proj = PROJECT_MAP.get(project)
    if not proj:
        raise ValueError(
            f"Unknown project: {project}. "
            f"Available: {', '.join(PROJECT_MAP.keys())}"
        )
    env_suffix = ENV_MAP.get(env)
    if not env_suffix:
        raise ValueError(
            f"Unknown env: {env}. Available: {', '.join(ENV_MAP.keys())}"
        )
    return f"{CONFIG_PREFIX}_{proj}_{env_suffix}_odps_config.ini"


# ── SQL Safety ──────────────────────────────────────────

def is_readonly_sql(sql: str) -> tuple[bool, str]:
    """Check if SQL is read-only. Returns (is_safe, error_message)."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        return False, "Empty SQL"

    upper = stripped.upper()
    if not upper.startswith(READONLY_PREFIXES):
        return False, f"SQL must start with one of: {', '.join(READONLY_PREFIXES)}"

    # Check for multiple statements
    if ";" in stripped:
        parts = [p.strip() for p in stripped.split(";") if p.strip()]
        if len(parts) > 1:
            return False, "Multiple SQL statements are not allowed"

    # Check for forbidden keywords
    for kw in FORBIDDEN_KEYWORDS:
        pattern = rf"\b{kw}\b"
        if re.search(pattern, upper):
            return False, f"Forbidden keyword: {kw}"

    return True, ""


def ensure_limit(sql: str, default_limit: int = 1000) -> str:
    """Ensure SQL has a LIMIT clause."""
    upper = sql.strip().upper()
    if "LIMIT" in upper:
        return sql
    return sql.rstrip(";").rstrip() + f"\nLIMIT {default_limit}"


# ── Output Parsers ──────────────────────────────────────

def _parse_table_format(lines: list[str]) -> dict | None:
    """Parse odpscmd box-drawing table format."""
    data_lines = []
    header_line = None
    border_count = 0
    in_table = False

    for line in lines:
        trimmed = line.strip()
        if re.match(r"^\+[-+]+\+$", trimmed):
            border_count += 1
            if not in_table:
                in_table = True
                continue
            if border_count >= 3:
                break
            continue
        if in_table and trimmed.startswith("|") and trimmed.endswith("|"):
            if not header_line:
                header_line = trimmed
            else:
                data_lines.append(trimmed)

    if not header_line:
        return None

    columns = [c.strip() for c in header_line.split("|")]
    columns = [c for c in columns if c]

    rows = []
    for line in data_lines:
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]
        while len(cells) < len(columns):
            cells.append("")
        rows.append(cells[: len(columns)])

    return {"columns": columns, "rows": rows}


def _parse_tab_format(lines: list[str]) -> dict | None:
    """Parse TSV fallback."""
    data_lines = [
        line
        for line in lines
        if line.strip()
        and not any(line.strip().startswith(p) for p in NOISE_PREFIXES)
    ]
    if len(data_lines) < 2 or "\t" not in data_lines[0]:
        return None
    columns = [c.strip() for c in data_lines[0].split("\t")]
    rows = [[c.strip() for c in line.split("\t")] for line in data_lines[1:]]
    return {"columns": columns, "rows": rows}


def _parse_pipe_format(lines: list[str]) -> dict | None:
    """Parse pipe-delimited without borders."""
    data_lines = [l for l in lines if l.strip().startswith("|") and l.strip().endswith("|")]
    if len(data_lines) < 2:
        return None
    columns = [c.strip() for c in data_lines[0].split("|") if c.strip()]
    rows = []
    for line in data_lines[1:]:
        cells = [c.strip() for c in line.split("|") if c.strip()]
        while len(cells) < len(columns):
            cells.append("")
        rows.append(cells[: len(columns)])
    return {"columns": columns, "rows": rows}


def _parse_text_lines(output: str) -> dict | None:
    """Parse plain text lines (one item per line, e.g. SHOW TABLES output)."""
    lines = output.split("\n")
    lines = [l.strip() for l in lines if l.strip()]
    lines = [
        l for l in lines
        if not any(l.startswith(p) for p in NOISE_PREFIXES)
    ]
    if not lines:
        return None
    # SHOW TABLES output: each line may be prefixed with RAM$owner:id:
    cleaned = []
    for l in lines:
        if ":" in l and l.startswith("RAM$"):
            parts = l.split(":")
            table_name = parts[-1].strip()
            if table_name:
                cleaned.append(table_name)
        else:
            cleaned.append(l)
    if not cleaned:
        return None
    return {"columns": ["table_name"], "rows": [[name] for name in cleaned]}


def parse_odps_output(output: str) -> dict:
    """Parse odpscmd stdout into columns + rows. Tries multiple formats."""
    lines = output.split("\n")

    table = _parse_table_format(lines)
    if table and table["columns"]:
        return {**table, "raw_output": output}

    tab = _parse_tab_format(lines)
    if tab and tab["columns"]:
        return {**tab, "raw_output": output}

    pipe = _parse_pipe_format(lines)
    if pipe and pipe["columns"]:
        return {**pipe, "raw_output": output}

    text = _parse_text_lines(output)
    if text and text["rows"]:
        return {**text, "raw_output": output}

    return {"columns": [], "rows": [], "raw_output": output}


# ── Logview Extraction ─────────────────────────────────

def _extract_logview(output: str) -> str | None:
    m = re.search(r"https?://\S*logview\S*", output)
    return m.group(0) if m else None


# ── Core Execution ──────────────────────────────────────

def execute_odps(
    sql: str,
    project: str = "zabank_dw",
    env: str = "prd",
    timeout: int = 300,
    auto_limit: bool = True,
) -> OdpsQueryResult:
    """
    Execute a read-only SQL on ODPS via SSH + odpscmd.

    Args:
        sql: Read-only SQL statement
        project: ODPS project name
        env: Environment (prd/test/dev)
        timeout: SSH timeout in seconds
        auto_limit: If True, append LIMIT 1000 if missing

    Returns:
        OdpsQueryResult with columns, rows, and metadata
    """
    import time

    start = time.time()

    # Safety check
    is_safe, error_msg = is_readonly_sql(sql)
    if not is_safe:
        return OdpsQueryResult(
            status="error",
            error_message=error_msg,
            duration_ms=int((time.time() - start) * 1000),
        )

    # Auto LIMIT
    if auto_limit and sql.strip().upper().startswith("SELECT"):
        sql = ensure_limit(sql)

    # Build remote command
    config_path = get_config_path(project, env)
    escaped_sql = sql.replace('"', '\\"')
    remote_cmd = (
        f"{ODPSCMD_PATH} --config={config_path} "
        f'--project={project} -e "{escaped_sql}"'
    )

    # Run SSH
    try:
        proc = subprocess.run(
            [
                SSH_CMD,
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "MACs=hmac-sha2-256",
                SSH_HOST,
                remote_cmd,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return OdpsQueryResult(
            status="error",
            error_message=f"ODPS query timed out ({timeout}s)",
            duration_ms=int((time.time() - start) * 1000),
        )
    except Exception as e:
        return OdpsQueryResult(
            status="error",
            error_message=f"SSH execution failed: {e}",
            duration_ms=int((time.time() - start) * 1000),
        )

    # Check stderr for errors
    stderr = proc.stderr or ""
    if stderr and "Authorized uses only" not in stderr:
        if any(kw in stderr for kw in ("FAILED", "ERROR", "Exception")):
            return OdpsQueryResult(
                status="error",
                error_message=f"ODPS execution error: {stderr}",
                raw_output=proc.stdout or "",
                duration_ms=int((time.time() - start) * 1000),
            )

    # Parse stdout
    stdout = proc.stdout or ""
    parsed = parse_odps_output(stdout)

    columns = [{"name": c, "type": "string"} for c in parsed.get("columns", [])]
    raw_rows = parsed.get("rows", [])
    rows = []
    for row in raw_rows:
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col["name"]] = row[i] if i < len(row) else ""
        rows.append(row_dict)

    logview = _extract_logview(stdout)
    duration = int((time.time() - start) * 1000)

    return OdpsQueryResult(
        columns=columns,
        rows=rows,
        raw_output=stdout,
        logview_url=logview,
        duration_ms=duration,
        status="success",
    )


# ── Metadata Helpers ────────────────────────────────────

def list_tables(project: str = "zabank_dw", env: str = "prd") -> OdpsQueryResult:
    """SHOW TABLES in a project."""
    return execute_odps("SHOW TABLES", project=project, env=env, auto_limit=False)


def desc_table(table_name: str, project: str = "zabank_dw", env: str = "prd") -> OdpsQueryResult:
    """DESC a table."""
    return execute_odps(f"DESC {table_name}", project=project, env=env, auto_limit=False)


def show_partitions(table_name: str, project: str = "zabank_dw", env: str = "prd") -> OdpsQueryResult:
    """SHOW PARTITIONS for a table."""
    return execute_odps(
        f"SHOW PARTITIONS {table_name}",
        project=project,
        env=env,
        auto_limit=False,
    )


def check_connection(project: str = "zabank_dw", env: str = "prd") -> bool:
    """Quick connectivity check."""
    result = execute_odps("SELECT 1", project=project, env=env, auto_limit=True)
    return result.status == "success"
