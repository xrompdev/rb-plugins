---
name: schema
description: Inspect table schema, columns, indexes, and relationships in MySQL or PostgreSQL
argument-hint: "<mysql|postgres> [table_name]"
allowed-tools:
  - Bash
  - AskUserQuestion
---

Inspect database schema information for a specific table or all tables.

## Instructions

1. Parse the user's arguments:
   - **Database target**: `mysql` (main) or `postgres`/`payment` (payment database)
   - **Table name** (optional): Specific table to inspect

2. If no database target is specified, ask which database.

3. **Ask for the database connection string** using AskUserQuestion:
   - For MySQL: "Please provide your DATABASE_URL (format: mysql://user:password@host:port/database)"
   - For PostgreSQL: "Please provide your PAYMENT_DATABASE_URL (format: postgresql://user:password@host:port/database)"

4. **Test the connection**:
   - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT 1"`
   - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT 1"`
   - If the test fails, show the error and ask the user to verify their credentials.

5. Execute the appropriate schema inspection:

### MySQL (main database)
- **All tables**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "CONNECTION_URL" "SHOW TABLES"`
- **Table schema**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "CONNECTION_URL" "DESCRIBE table_name"`
- **Table indexes**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "CONNECTION_URL" "SHOW INDEX FROM table_name"`
- **Create statement**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "CONNECTION_URL" "SHOW CREATE TABLE table_name"`

### PostgreSQL (payment database)
- **All tables**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "CONNECTION_URL" "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"`
- **Table schema**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "CONNECTION_URL" "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'table_name' ORDER BY ordinal_position"`
- **Table indexes**: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "CONNECTION_URL" "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'table_name'"`

6. **Always show the SQL query** to the user in a fenced SQL code block before presenting results, so the user can see exactly what was executed.

7. Present the schema information in a clear, organized format.

## Examples

- `/db:schema mysql users` - Show columns and indexes for users table
- `/db:schema postgres` - List all tables in payment database
- `/db:schema mysql` - List all tables in main database
