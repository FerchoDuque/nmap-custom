"""Baseline schema: scans, scan_results, ports and schedules.

This is the schema that `Base.metadata.create_all()` produced for 0.1.0.
Databases created before Alembic was introduced must be adopted with
`alembic stamp 0001` (see `app.core.db_migrations.ensure_schema`).

Revision ID: 0001
Revises:
Create Date: 2026-11-21
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCAN_TYPE = sa.Enum(
    "TCP_CONNECT", "TCP_SYN", "UDP", "COMPREHENSIVE", name="scantype"
)
SCAN_STATUS = sa.Enum(
    "PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="scanstatus"
)
PORT_STATE = sa.Enum("OPEN", "CLOSED", "FILTERED", "UNKNOWN", name="portstate")


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("scan_type", SCAN_TYPE, nullable=False),
        sa.Column("status", SCAN_STATUS, nullable=True),
        sa.Column("port_range", sa.String(length=255), nullable=True),
        sa.Column("service_detection", sa.Boolean(), nullable=True),
        sa.Column("os_detection", sa.Boolean(), nullable=True),
        sa.Column("aggressive", sa.Boolean(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("current_host", sa.String(length=255), nullable=True),
        sa.Column("hosts_total", sa.Integer(), nullable=True),
        sa.Column("hosts_scanned", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_hosts_up", sa.Integer(), nullable=True),
        sa.Column("total_ports_found", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scans_created_at", "scans", ["created_at"])
    op.create_index("ix_scans_id", "scans", ["id"])
    op.create_index("ix_scans_status", "scans", ["status"])
    op.create_index("ix_scans_target", "scans", ["target"])
    op.create_index("ix_scans_task_id", "scans", ["task_id"])

    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scan_config", sa.JSON(), nullable=False),
        sa.Column("cron_expression", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("total_runs", sa.Integer(), nullable=True),
        sa.Column("successful_runs", sa.Integer(), nullable=True),
        sa.Column("failed_runs", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedules_enabled", "schedules", ["enabled"])
    op.create_index("ix_schedules_id", "schedules", ["id"])

    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("mac_address", sa.String(length=17), nullable=True),
        sa.Column("is_up", sa.Boolean(), nullable=True),
        sa.Column("os_name", sa.String(length=255), nullable=True),
        sa.Column("os_accuracy", sa.Integer(), nullable=True),
        sa.Column("os_details", sa.JSON(), nullable=True),
        sa.Column("latency", sa.Integer(), nullable=True),
        sa.Column("scanned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_results_id", "scan_results", ["id"])
    op.create_index("ix_scan_results_ip_address", "scan_results", ["ip_address"])
    op.create_index("ix_scan_results_scan_id", "scan_results", ["scan_id"])

    op.create_table(
        "ports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("port_number", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=10), nullable=False),
        sa.Column("state", PORT_STATE, nullable=False),
        sa.Column("service_name", sa.String(length=255), nullable=True),
        sa.Column("service_product", sa.String(length=255), nullable=True),
        sa.Column("service_version", sa.String(length=255), nullable=True),
        sa.Column("service_extra_info", sa.Text(), nullable=True),
        sa.Column("banner", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["result_id"], ["scan_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ports_id", "ports", ["id"])
    op.create_index("ix_ports_port_number", "ports", ["port_number"])
    op.create_index("ix_ports_result_id", "ports", ["result_id"])


def downgrade() -> None:
    op.drop_table("ports")
    op.drop_table("scan_results")
    op.drop_table("schedules")
    op.drop_table("scans")

    # PostgreSQL keeps native ENUM types after dropping the tables; without
    # this, re-running `upgrade` fails with "type already exists".
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        PORT_STATE.drop(bind, checkfirst=True)
        SCAN_STATUS.drop(bind, checkfirst=True)
        SCAN_TYPE.drop(bind, checkfirst=True)
