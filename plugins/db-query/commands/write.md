---
name: write
description: Insert records into MySQL (main) or PostgreSQL (payment) database (localhost only)
argument-hint: "<mysql|postgres> <description of what to insert>"
allowed-tools:
  - Bash
  - AskUserQuestion
---

Insert new records into a local database based on the user's request.

## Instructions

1. Parse the user's arguments to determine:
   - **Database target**: `mysql` (main database) or `postgres`/`payment` (payment database)
   - **What to insert**: A description of the record(s) to create, or a raw INSERT statement

2. If no database target is specified, ask which database to insert into.

3. If the description is vague, ask clarifying questions about what data to insert.

4. **Ask for the database connection string** using AskUserQuestion:
   - For MySQL: "Please provide your DATABASE_URL (format: mysql://user:password@host:port/database)"
   - For PostgreSQL: "Please provide your PAYMENT_DATABASE_URL (format: postgresql://user:password@host:port/database)"

5. **Validate localhost connection**: The connection URL MUST point to localhost (127.0.0.1, localhost, or a Docker service name). If the URL contains a remote host, **refuse immediately** and explain that write operations are restricted to local databases only.

6. **Test the connection** before proceeding:
   - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT 1"`
   - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT 1"`
   - If the test fails, show the error and ask the user to verify their credentials.

7. **Inspect the target table schema** to build a correct INSERT statement:
   - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "DESCRIBE table_name"`
   - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'table_name' ORDER BY ordinal_position"`

8. **Build the INSERT statement** based on the schema and user's request. Respect:
   - Required columns (NOT NULL without defaults)
   - Column data types
   - Auto-increment / serial columns (omit from INSERT)
   - Default values (omit columns where the default is acceptable)

9. **Show the INSERT statement and ask for confirmation** using AskUserQuestion:
   - Display the full SQL in a fenced code block
   - Show a summary of what will be inserted (table name, number of rows, key values)
   - Present options:
     - "Yes, execute this INSERT"
     - "No, cancel"
     - "Modify the query" (let user adjust values)

10. **Only after user confirms**, execute the INSERT:
    - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/write-mysql.sh "$DATABASE_URL" "INSERT_QUERY"`
    - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/write-postgres.sh "$PAYMENT_DATABASE_URL" "INSERT_QUERY"`

11. After execution, **verify the insert** by querying for the newly created record(s):
    - MySQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-mysql.sh "$DATABASE_URL" "SELECT * FROM table_name WHERE ... ORDER BY id DESC LIMIT 5"`
    - PostgreSQL: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/query-postgres.sh "$PAYMENT_DATABASE_URL" "SELECT * FROM table_name WHERE ... ORDER BY id DESC LIMIT 5"`

12. Present the result to the user, confirming the record was created.

## Safety

- **Localhost only**: The write scripts enforce that the connection must be to localhost (127.0.0.1, ::1, or a Docker service name). Remote database writes are blocked at the script level.
- **INSERT only**: Only INSERT statements are allowed. UPDATE, DELETE, DROP, ALTER, and all other write operations are blocked by the script.
- **Confirmation required**: Never execute an INSERT without explicit user confirmation.
- **Schema-aware**: Always inspect the table schema before building the INSERT to avoid errors.
- **Verify after insert**: Always query back the inserted record to confirm success.

## Examples

- `/db:write mysql Create a test user with email test@example.com`
- `/db:write postgres Insert a payment event for invoice INV-001`
- `/db:write mysql INSERT INTO users (name, email) VALUES ('Test User', 'test@example.com')`
