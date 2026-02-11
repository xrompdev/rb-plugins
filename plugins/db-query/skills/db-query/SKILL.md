---
name: db-query
description: >
  Use when the user is troubleshooting, debugging, or investigating issues that involve database data.
  Also use when the user asks about data in the database, wants to verify records, check table structure,
  inspect relationships, count rows, or understand the current state of data. Triggers on keywords like
  "check the database", "what's in the table", "query the data", "look at the records", "debug this data",
  "why is this record", "troubleshoot", "investigate", "verify in db", "check db", "data looks wrong",
  "missing data", "duplicate records", "show me the data".
version: 0.1.0
---

# Local Database Query Skill

Query the local MySQL and PostgreSQL databases to help with troubleshooting, debugging, and data investigation. This skill provides read-only access to two databases.

## Databases

- **MySQL (main)**: Main application database. Use for all core business data (users, invoices, bids, companies, etc.).
- **PostgreSQL (payment)**: Payment service database with event sourcing. Use for payment events, projections, and financial data.

## Credential Flow

Before querying, you MUST ask the user for the appropriate connection string using AskUserQuestion:
- For MySQL (main database): "Please provide your DATABASE_URL (format: mysql://user:password@host:port/database)"
- For PostgreSQL (payment database): "Please provide your PAYMENT_DATABASE_URL (format: postgresql://user:password@host:port/database)"

Then **test the connection** before running any actual queries:
- MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT 1"`
- PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT 1"`

If the test fails, show the error and ask the user to verify their credentials. Do not proceed until a successful connection is confirmed.

## How to Query

Execute read-only SQL using the query scripts. Both scripts take the connection URL as the first argument and the SQL query as the second:

- **MySQL**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SQL_QUERY"`
- **PostgreSQL**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SQL_QUERY"`

Docker auto-detection: if the host in the URL is a Docker service name (e.g. `mysql`, `postgres`), the script automatically remaps to the exposed localhost port.

## Allowed Operations

- `SELECT` queries (with JOINs, WHERE, GROUP BY, ORDER BY, LIMIT, subqueries, CTEs)
- `SHOW` commands (TABLES, DATABASES, CREATE TABLE, INDEX, etc.)
- `DESCRIBE` / `DESC` (MySQL table structure)
- `EXPLAIN` (query execution plans)

## Prohibited Operations

All write and schema-modification operations are blocked by the scripts. Do not attempt: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, or any other data/schema modification.

## When to Query Proactively

When the user is debugging or troubleshooting and you need data context, ask for the DB credentials and query the database directly rather than asking the user to look it up manually. Situations include:

- Investigating why a feature isn't working as expected
- Verifying data integrity or record existence
- Checking relationships between entities
- Understanding current state of business data
- Confirming event sourcing state in payment system
- Diagnosing data-related bugs or inconsistencies

## Query Patterns

### Discover schema first
Before querying specific data, inspect the table structure:
```bash
# MySQL
bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "DESCRIBE table_name"
bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SHOW TABLES"

# PostgreSQL
bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'table_name' ORDER BY ordinal_position"
```

### Limit results
Always use LIMIT to avoid overwhelming output:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT * FROM users LIMIT 10"
```

### Count before fetching
Check data volume before retrieving:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT COUNT(*) FROM invoices WHERE status = 'pending'"
```

## Best Practices

1. Always ask for credentials before the first query in a session
2. Always test the connection before running actual queries
3. **Always show the SQL query** to the user before presenting results. Display it in a fenced SQL code block so the user can see exactly what was executed.
4. Always LIMIT query results (start with 10-20 rows)
5. Inspect schema before writing complex queries
6. Use COUNT(*) first to understand data volume
7. Choose the right database: core business data is in MySQL, payment/event data is in PostgreSQL
8. Present query results clearly with context about what was found
9. If a query fails with a connection error, inform the user that the database may not be running locally
