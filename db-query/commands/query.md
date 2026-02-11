---
name: query
description: Run a read-only SQL query against MySQL (main) or PostgreSQL (payment) database
argument-hint: "<mysql|postgres> <SQL query>"
allowed-tools:
  - Bash
  - AskUserQuestion
---

Run a read-only SQL query against one of the local databases.

## Instructions

1. Parse the user's arguments to determine:
   - **Database target**: `mysql` (main database) or `postgres`/`payment` (payment database)
   - **SQL query**: The query to execute

2. If no database target is specified, ask which database to query.

3. If no SQL query is provided, ask what the user wants to query.

4. **Ask for the database connection string** using AskUserQuestion:
   - For MySQL: "Please provide your DATABASE_URL (format: mysql://user:password@host:port/database)"
   - For PostgreSQL: "Please provide your PAYMENT_DATABASE_URL (format: postgresql://user:password@host:port/database)"

5. **Test the connection** before running the actual query:
   - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT 1"`
   - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT 1"`
   - If the test fails, show the error and ask the user to verify their credentials.

6. **Execute the query** using the provided value:
   - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SQL_QUERY"`
   - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SQL_QUERY"`

7. **Always show the SQL query** to the user in a fenced SQL code block before presenting results, so the user can see exactly what was executed.

8. Present the results in a readable format. For large result sets, summarize and show key data.

## Safety

- The scripts enforce read-only operations. Only SELECT, SHOW, DESCRIBE, and EXPLAIN are allowed.
- If a user asks for a write operation, refuse and explain that this plugin is read-only.
- Docker auto-detection: if the host in the URL is a Docker service name, the script automatically remaps to the exposed localhost port.

## Examples

- `/db:query mysql SELECT * FROM users LIMIT 5`
- `/db:query postgres SELECT * FROM payment_events ORDER BY created_at DESC LIMIT 10`
- `/db:query mysql SHOW TABLES`
- `/db:query mysql DESCRIBE invoices`
