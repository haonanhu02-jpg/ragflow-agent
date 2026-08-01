"""AST-validated, tenant-forced, read-only SQL Tool."""

from __future__ import annotations

import sqlglot
from pydantic import BaseModel, ConfigDict, Field
from sqlglot import exp

from ragflow_agent.agent.domain.agentic import (
    ToolAuthorizationContext,
    ToolEffect,
    ToolInvocation,
    ToolRegistration,
    ToolRiskLevel,
)
from ragflow_agent.agent.domain.errors import AgentToolError
from ragflow_agent.agent.ports.agentic import ReadOnlySqlExecutorPort


class SqlToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(min_length=1, max_length=20_000)
    parameters: dict[str, object] = Field(default_factory=dict)


class SqlAllowlist(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    database_name: str | None = None
    schema_name: str | None = None
    tables: dict[str, tuple[str, ...]] = Field(min_length=1)
    tenant_column: str = "tenant_id"
    allowed_functions: tuple[str, ...] = (
        "avg",
        "coalesce",
        "count",
        "date_trunc",
        "lower",
        "max",
        "min",
        "sum",
        "upper",
    )


class ReadOnlySqlTool:
    """Render only a validated single query through an isolated executor Port."""

    def __init__(
        self,
        *,
        executor: ReadOnlySqlExecutorPort,
        allowlist: SqlAllowlist,
        max_rows: int = 200,
        timeout_seconds: float = 5,
        sensitive_fields: tuple[str, ...] = (),
    ) -> None:
        self._executor = executor
        self._allowlist = allowlist
        self._max_rows = max_rows
        self._timeout_seconds = timeout_seconds
        self._registration = ToolRegistration(
            tool_name="readonly_sql",
            version="1",
            description="Run one tenant-scoped SELECT against an explicit table/column allowlist.",
            input_schema=SqlToolInput.model_json_schema(),
            output_schema={"type": "array"},
            effect=ToolEffect.READ_ONLY,
            risk_level=ToolRiskLevel.MEDIUM,
            timeout_seconds=timeout_seconds,
            max_retries=0,
            max_output_bytes=1_000_000,
            idempotent=True,
            requires_hitl=False,
            sensitive_fields=sensitive_fields,
        )

    @property
    def registration(self) -> ToolRegistration:
        return self._registration

    async def invoke(
        self,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
    ) -> object:
        payload = SqlToolInput.model_validate(invocation.arguments)
        statement = validate_and_scope_sql(
            payload.statement,
            allowlist=self._allowlist,
        )
        if "_agent_tenant_id" in payload.parameters or "_agent_limit" in payload.parameters:
            raise AgentToolError(
                "reserved SQL parameters cannot be supplied by the model",
                error_code="sql_reserved_parameter",
            )
        parameters: dict[str, object] = dict(payload.parameters)
        parameters["_agent_tenant_id"] = context.tenant_id
        parameters["_agent_limit"] = self._max_rows
        try:
            rows = await self._executor.execute(
                statement=statement,
                parameters=parameters,
                timeout_seconds=self._timeout_seconds,
                max_rows=self._max_rows,
            )
        except AgentToolError:
            raise
        except Exception as exc:
            raise AgentToolError(
                "read-only SQL execution failed",
                error_code="sql_execution_failed",
                status_code=502,
                details={"exception_type": type(exc).__name__},
            ) from exc
        return [dict(row) for row in rows[: self._max_rows]]


def validate_and_scope_sql(statement: str, *, allowlist: SqlAllowlist) -> str:
    """Parse one query, reject unsafe AST nodes, and inject tenant filtering."""
    try:
        expressions = sqlglot.parse(statement, read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise AgentToolError("SQL parsing failed", error_code="sql_invalid") from exc
    if len(expressions) != 1 or not isinstance(expressions[0], exp.Query):
        raise AgentToolError(
            "only one SELECT or read-only CTE is allowed",
            error_code="sql_not_read_only",
        )
    query = expressions[0]
    forbidden_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Merge,
        exp.Create,
        exp.Drop,
        exp.Alter,
        exp.Command,
        exp.Transaction,
    )
    if any(query.find(node_type) is not None for node_type in forbidden_types):
        raise AgentToolError("SQL contains a forbidden operation", error_code="sql_not_read_only")

    cte_names = {cte.alias_or_name.lower() for cte in query.find_all(exp.CTE)}
    tables = tuple(
        table for table in query.find_all(exp.Table) if table.name.lower() not in cte_names
    )
    if not tables:
        raise AgentToolError("SQL must reference an allowed table", error_code="sql_table_denied")
    allowed_tables = {name.lower(): columns for name, columns in allowlist.tables.items()}
    for table in tables:
        name = table.name.lower()
        if name not in allowed_tables:
            raise AgentToolError(
                "SQL references a table outside the allowlist",
                error_code="sql_table_denied",
                details={"table": table.name},
            )
        if allowlist.database_name:
            if table.catalog.lower() != allowlist.database_name.lower():
                raise AgentToolError(
                    "SQL database is not allowed", error_code="sql_database_denied"
                )
        elif table.catalog:
            raise AgentToolError("SQL database is not allowed", error_code="sql_database_denied")
        if allowlist.schema_name:
            if table.db.lower() != allowlist.schema_name.lower():
                raise AgentToolError("SQL schema is not allowed", error_code="sql_schema_denied")
        elif table.db:
            raise AgentToolError("SQL schema is not allowed", error_code="sql_schema_denied")

    if query.find(exp.Star) is not None:
        raise AgentToolError("SELECT * is not allowed", error_code="sql_column_denied")
    if any(literal.is_string for literal in query.find_all(exp.Literal)):
        raise AgentToolError(
            "string values must be supplied as bound parameters",
            error_code="sql_parameter_required",
        )
    allowed_functions = {name.lower() for name in allowlist.allowed_functions}
    for function in query.find_all(exp.Func):
        name = function.name if isinstance(function, exp.Anonymous) else type(function).__name__
        if name.lower() not in allowed_functions:
            raise AgentToolError(
                "SQL function is outside the allowlist",
                error_code="sql_function_denied",
                details={"function": name},
            )
    aliases = {
        table.alias_or_name.lower(): set(allowed_tables[table.name.lower()]) for table in tables
    }
    for column in query.find_all(exp.Column):
        if column.table:
            columns = aliases.get(column.table.lower())
        elif len(tables) == 1:
            columns = set(allowed_tables[tables[0].name.lower()])
        else:
            columns = None
        if columns is None or column.name.lower() not in {name.lower() for name in columns}:
            raise AgentToolError(
                "SQL references a column outside the allowlist",
                error_code="sql_column_denied",
                details={"column": column.name},
            )
    tenant_column = allowlist.tenant_column.replace('"', "")
    for table in tables:
        physical_table = table.copy()
        physical_table.set("alias", None)
        scoped_query = sqlglot.parse_one(
            f'SELECT * FROM {physical_table.sql()} WHERE "{tenant_column}" = :_agent_tenant_id',
            read="postgres",
        )
        alias = exp.TableAlias(this=exp.to_identifier(table.alias_or_name, quoted=True))
        table.replace(exp.Subquery(this=scoped_query, alias=alias))
    normalized = query.sql()
    return f'SELECT * FROM ({normalized}) AS "_agent_allowed" LIMIT :_agent_limit'
