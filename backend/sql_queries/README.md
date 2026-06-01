# SQL Queries

Database setup and analytics SQL scripts used by the n8n pipeline and reporting dashboards.

## File

- `sql_queries.txt`: end-to-end PostgreSQL script set for schema creation, table/index setup, materialized views, trigger logic, and verification queries

## What It Covers

- `rag_analytics` schema bootstrap
- Session-level analytics table setup
- Field-level analytics table setup
- Indexes for query performance
- Materialized views for dashboard metrics
- Trigger and refresh lifecycle support
- Verification queries for migration confidence

## Typical Workflow

1. Review script sections and adapt to your environment.
2. Execute against your PostgreSQL instance.
3. Validate created objects and row counts.
4. Connect n8n PostgreSQL nodes to resulting schema.

## Caution

Always run database scripts first in staging or development before production rollout.
