"""Classify and apply schema-only BigQuery bootstrap statements safely."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from google.cloud import bigquery

from panganlens.bootstrap_plan import build_bootstrap_plan
from panganlens.warehouse.loader import PROJECT_ID_PATTERN

DEFAULT_LOCATION = "asia-southeast2"
DEFAULT_STATEMENT_TIMEOUT_SECONDS = 120.0
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
PANGANLENS_DATASET_PATTERN = r"panganlens_(?:raw|staging|core|mart|ops)"

EXECUTE = "EXECUTE"
SKIP_AUDIT = "SKIP_AUDIT"


@dataclass(frozen=True, slots=True)
class BootstrapStatement:
    file_order: int
    statement_order: int
    filename: str
    kind: str
    action: str
    sha256: str
    bytes: int
    sql: str

    def as_dict(self) -> dict[str, object]:
        return {
            "file_order": self.file_order,
            "statement_order": self.statement_order,
            "filename": self.filename,
            "kind": self.kind,
            "action": self.action,
            "sha256": self.sha256,
            "bytes": self.bytes,
        }


@dataclass(frozen=True, slots=True)
class BootstrapExecutionPlan:
    status: str
    plan_sha256: str
    statements: tuple[BootstrapStatement, ...]
    operational_files_excluded: tuple[str, ...]

    @property
    def executable_statements(self) -> tuple[BootstrapStatement, ...]:
        return tuple(statement for statement in self.statements if statement.action == EXECUTE)

    @property
    def audit_statements(self) -> tuple[BootstrapStatement, ...]:
        return tuple(statement for statement in self.statements if statement.action == SKIP_AUDIT)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "plan_sha256": self.plan_sha256,
            "executable_statement_count": len(self.executable_statements),
            "audit_statement_count": len(self.audit_statements),
            "statements": [statement.as_dict() for statement in self.statements],
            "operational_files_excluded": list(self.operational_files_excluded),
            "requires_explicit_apply": True,
        }


@dataclass(frozen=True, slots=True)
class BootstrapExecutionResult:
    status: str
    project_id: str
    location: str
    plan_sha256: str
    applied_statement_count: int
    skipped_audit_statement_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "project_id": self.project_id,
            "location": self.location,
            "plan_sha256": self.plan_sha256,
            "applied_statement_count": self.applied_statement_count,
            "skipped_audit_statement_count": self.skipped_audit_statement_count,
        }


def split_sql_statements(sql: str) -> tuple[str, ...]:
    """Split SQL on statement terminators while respecting strings and comments."""

    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            buffer.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            buffer.append(char)
            if char == "*" and next_char == "/":
                buffer.append(next_char)
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if quote is not None:
            buffer.append(char)
            if char == "\\" and quote in {"'", '"'} and next_char:
                buffer.append(next_char)
                index += 2
                continue
            if char == quote:
                if quote in {"'", '"'} and next_char == quote:
                    buffer.append(next_char)
                    index += 2
                    continue
                quote = None
            index += 1
            continue

        if char == "-" and next_char == "-":
            buffer.extend((char, next_char))
            in_line_comment = True
            index += 2
            continue

        if char == "/" and next_char == "*":
            buffer.extend((char, next_char))
            in_block_comment = True
            index += 2
            continue

        if char in {"'", '"', "`"}:
            quote = char
            buffer.append(char)
            index += 1
            continue

        if char == ";":
            statement = "".join(buffer).strip()
            if _normalized_sql(statement):
                statements.append(statement)
            buffer = []
            index += 1
            continue

        buffer.append(char)
        index += 1

    if quote is not None:
        raise RuntimeError("bootstrap SQL contains an unterminated quoted value")
    if in_block_comment:
        raise RuntimeError("bootstrap SQL contains an unterminated block comment")

    tail = "".join(buffer).strip()
    if _normalized_sql(tail):
        statements.append(tail)
    return tuple(statements)


def classify_bootstrap_statement(sql: str) -> tuple[str, str]:
    """Return the reviewed statement kind and whether it may execute."""

    normalized = _normalized_sql(sql)
    upper = normalized.upper()

    schema_pattern = rf"^CREATE SCHEMA IF NOT EXISTS {PANGANLENS_DATASET_PATTERN}\b"
    table_pattern = (
        rf"^CREATE TABLE IF NOT EXISTS {PANGANLENS_DATASET_PATTERN}\.[A-Z0-9_]+\b"
    )
    view_pattern = (
        rf"^CREATE OR REPLACE VIEW {PANGANLENS_DATASET_PATTERN}\.[A-Z0-9_]+\b"
    )

    if re.match(schema_pattern, upper):
        return "CREATE_SCHEMA", EXECUTE
    if re.match(table_pattern, upper):
        if re.search(r"\bAS\s+(?:SELECT|WITH)\b", upper):
            raise RuntimeError("CREATE TABLE AS query is not allowed in schema bootstrap")
        return "CREATE_TABLE", EXECUTE
    if re.match(view_pattern, upper):
        return "CREATE_VIEW", EXECUTE
    if re.match(r"^SELECT\b", upper):
        return "READ_ONLY_AUDIT", SKIP_AUDIT

    preview = normalized[:80]
    raise RuntimeError(f"unclassified bootstrap statement: {preview}")


def build_bootstrap_execution_plan(repo_root: str | Path) -> BootstrapExecutionPlan:
    """Classify every schema file statement and return an immutable apply manifest."""

    root = Path(repo_root).resolve()
    file_plan = build_bootstrap_plan(root)
    statements: list[BootstrapStatement] = []

    for file_step in file_plan.steps:
        sql_path = root / "sql" / file_step.filename
        sql_text = sql_path.read_text(encoding="utf-8")
        for statement_order, sql in enumerate(split_sql_statements(sql_text), start=1):
            kind, action = classify_bootstrap_statement(sql)
            payload = sql.encode("utf-8")
            statements.append(
                BootstrapStatement(
                    file_order=file_step.order,
                    statement_order=statement_order,
                    filename=file_step.filename,
                    kind=kind,
                    action=action,
                    sha256=hashlib.sha256(payload).hexdigest(),
                    bytes=len(payload),
                    sql=sql,
                )
            )

    if not statements:
        raise RuntimeError("bootstrap execution plan has no classified statements")
    if not any(statement.action == EXECUTE for statement in statements):
        raise RuntimeError("bootstrap execution plan has no executable schema statements")

    digest = hashlib.sha256()
    for file_step in file_plan.steps:
        digest.update(
            f"file:{file_step.order}:{file_step.filename}:{file_step.sha256}\n".encode()
        )
    for statement in statements:
        digest.update(
            (
                f"statement:{statement.file_order}:{statement.statement_order}:"
                f"{statement.kind}:{statement.action}:{statement.sha256}\n"
            ).encode()
        )

    return BootstrapExecutionPlan(
        status="CLASSIFIED_SCHEMA_ONLY",
        plan_sha256=digest.hexdigest(),
        statements=tuple(statements),
        operational_files_excluded=file_plan.operational_files_excluded,
    )


class BigQueryBootstrapExecutor:
    """Apply only reviewed schema DDL after an exact plan hash confirmation."""

    def __init__(
        self,
        project_id: str,
        client: bigquery.Client | None = None,
        location: str = DEFAULT_LOCATION,
        statement_timeout_seconds: float = DEFAULT_STATEMENT_TIMEOUT_SECONDS,
    ) -> None:
        if not PROJECT_ID_PATTERN.fullmatch(project_id):
            raise ValueError("project_id is not a valid Google Cloud project ID")
        if statement_timeout_seconds <= 0:
            raise ValueError("statement_timeout_seconds must be positive")

        if client is not None:
            client_project = getattr(client, "project", project_id)
            if client_project != project_id:
                raise ValueError("BigQuery client project does not match project_id")

        self.project_id = project_id
        self.location = location
        self.statement_timeout_seconds = statement_timeout_seconds
        self.client = client or bigquery.Client(project=project_id, location=location)

    def apply(
        self,
        repo_root: str | Path,
        expected_plan_sha256: str,
    ) -> BootstrapExecutionResult:
        """Apply the exact reviewed plan and stop on the first failed statement."""

        if not SHA256_PATTERN.fullmatch(expected_plan_sha256):
            raise ValueError("expected_plan_sha256 must be a lowercase SHA-256 value")

        plan = build_bootstrap_execution_plan(repo_root)
        if expected_plan_sha256 != plan.plan_sha256:
            raise RuntimeError("bootstrap plan changed after review; generate and review it again")

        config = bigquery.QueryJobConfig(use_legacy_sql=False)
        applied = 0
        for statement in plan.executable_statements:
            job = self.client.query(
                statement.sql,
                job_config=config,
                location=self.location,
            )
            job.result(timeout=self.statement_timeout_seconds)
            applied += 1

        return BootstrapExecutionResult(
            status="SUCCESS",
            project_id=self.project_id,
            location=self.location,
            plan_sha256=plan.plan_sha256,
            applied_statement_count=applied,
            skipped_audit_statement_count=len(plan.audit_statements),
        )


def _normalized_sql(sql: str) -> str:
    without_comments = _remove_sql_comments(sql)
    return re.sub(r"\s+", " ", without_comments).strip()


def _remove_sql_comments(sql: str) -> str:
    output: list[str] = []
    quote: str | None = None
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            if char == "\n":
                output.append("\n")
                in_line_comment = False
            else:
                output.append(" ")
            index += 1
            continue

        if in_block_comment:
            if char == "*" and next_char == "/":
                output.extend((" ", " "))
                in_block_comment = False
                index += 2
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue

        if quote is not None:
            output.append(char)
            if char == "\\" and quote in {"'", '"'} and next_char:
                output.append(next_char)
                index += 2
                continue
            if char == quote:
                if quote in {"'", '"'} and next_char == quote:
                    output.append(next_char)
                    index += 2
                    continue
                quote = None
            index += 1
            continue

        if char == "-" and next_char == "-":
            output.extend((" ", " "))
            in_line_comment = True
            index += 2
            continue

        if char == "/" and next_char == "*":
            output.extend((" ", " "))
            in_block_comment = True
            index += 2
            continue

        if char in {"'", '"', "`"}:
            quote = char
        output.append(char)
        index += 1

    return "".join(output)
