---
name: tables
description: List all tables in MySQL (main) or PostgreSQL (payment) database with row counts
argument-hint: "[mysql|postgres|all]"
allowed-tools:
  - Bash
  - AskUserQuestion
---

List all tables in one or both databases, optionally with row counts.

## Instructions

1. Parse the user's arguments:
   - `mysql` - List tables in main MySQL database only
   - `postgres` or `payment` - List tables in payment PostgreSQL database only
   - `all` or no argument - List tables in both databases

2. **Ask for the database connection string(s)** using AskUserQuestion:
   - If querying MySQL (or both): "Please provide your DATABASE_URL (format: mysql://user:password@host:port/database)"
   - If querying PostgreSQL (or both): "Please provide your PAYMENT_DATABASE_URL (format: postgresql://user:password@host:port/database)"

3. **Test each connection** before listing:
   - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT 1"`
   - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT 1"`
   - If a test fails, show the error and ask the user to verify their credentials.

4. Execute the appropriate queries:

### MySQL (main database)
- **Table list with row counts**:
  ```
  bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "CONNECTION_URL" "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY table_name"
  ```

### PostgreSQL (payment database)
- **Table list**:
  ```
  bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "CONNECTION_URL" "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
  ```

5. **Always show the SQL query** to the user in a fenced SQL code block before presenting results, so the user can see exactly what was executed.

6. Present results as a clean table. When showing both databases, group them clearly under headers.

## Examples

- `/db:tables` - List all tables in both databases
- `/db:tables mysql` - List tables in main database
- `/db:tables postgres` - List tables in payment database
