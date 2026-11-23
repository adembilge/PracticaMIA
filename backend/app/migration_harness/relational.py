"""Fail-closed relational copy primitives for disposable migration rehearsal.

These helpers are intentionally not imported by application runtime code. They
copy only explicitly mapped columns inside a caller-owned transaction; they do
not connect to configured application databases or perform cutover/deletion.
"""
from __future__ import annotations

import re

from sqlalchemy import MetaData, Table, func, insert, select
from sqlalchemy.engine import Connection

from app.migration_harness.crypto import MigrationQuarantine

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _table(connection: Connection, qualified_name: str) -> Table:
    parts = qualified_name.split(".")
    if len(parts) not in (1, 2) or any(not _IDENTIFIER.fullmatch(p) for p in parts):
        raise ValueError("Invalid migration table identifier")
    schema, name = (parts[0], parts[1]) if len(parts) == 2 else (None, parts[0])
    return Table(name, MetaData(), schema=schema, autoload_with=connection)


def copy_table_rows(
    connection: Connection,
    *,
    source_table: str,
    target_table: str,
    column_map: dict[str, str] | None = None,
) -> int:
    """Copy a table using an explicit source→target column map.

    Unmapped columns retain their names. Every source column must map exactly
    once, every required target column must be supplied, and the target must be
    empty. Ciphertext/BYTEA values are copied unchanged; this function never
    decrypts, re-encrypts, transforms, or logs row values.
    """
    source = _table(connection, source_table)
    target = _table(connection, target_table)
    mapping = dict(column_map or {})
    source_names = set(source.c.keys())
    target_names = set(target.c.keys())

    if set(mapping) - source_names or set(mapping.values()) - target_names:
        raise MigrationQuarantine("relational_column_mapping_invalid")
    mapped_names = {mapping.get(name, name) for name in source_names}
    if len(mapped_names) != len(source_names) or not mapped_names <= target_names:
        raise MigrationQuarantine("relational_column_mapping_incomplete")

    required_target = {
        column.name for column in target.columns
        if not column.nullable
        and column.server_default is None
        and column.default is None
        and not getattr(column, "identity", None)
        and column.name not in mapped_names
    }
    if required_target:
        raise MigrationQuarantine("relational_target_required_columns_missing")

    existing = connection.execute(select(func.count()).select_from(target)).scalar_one()
    if existing:
        raise MigrationQuarantine("relational_target_not_empty")

    source_columns = []
    target_columns = []
    for source_name in source.c.keys():
        target_name = mapping.get(source_name, source_name)
        source_columns.append(source.c[source_name])
        target_columns.append(target.c[target_name])

    statement = insert(target).from_select(
        [column.name for column in target_columns],
        select(*source_columns),
    )
    connection.execute(statement)
    source_count = connection.execute(select(func.count()).select_from(source)).scalar_one()
    target_count = connection.execute(select(func.count()).select_from(target)).scalar_one()
    if source_count != target_count:
        raise MigrationQuarantine("relational_row_count_mismatch")
    return source_count


def assert_owner_consistency(
    connection: Connection,
    *,
    child_table: str,
    parent_table: str,
    child_parent_id: str,
    parent_id: str,
    child_owner: str = "owner_subject",
    parent_owner: str = "owner_subject",
) -> int:
    """Return zero only when every child has a same-owner, non-null parent."""
    child = _table(connection, child_table)
    parent = _table(connection, parent_table)
    for table, column in (
        (child, child_parent_id), (parent, parent_id),
        (child, child_owner), (parent, parent_owner),
    ):
        if column not in table.c:
            raise ValueError("Owner validation column does not exist")

    mismatch = connection.execute(
        select(func.count())
        .select_from(
            child.outerjoin(parent, child.c[child_parent_id] == parent.c[parent_id])
        )
        .where(
            parent.c[parent_id].is_(None)
            | parent.c[parent_owner].is_(None)
            | child.c[child_owner].is_(None)
            | (child.c[child_owner] != parent.c[parent_owner])
        )
    ).scalar_one()
    if mismatch:
        raise MigrationQuarantine("relational_owner_boundary_mismatch")
    return mismatch
