# db-query

Read-only database query tool for local MySQL and PostgreSQL databases.

## Commands

| Command | Description |
|---------|-------------|
| `/db-query:query <mysql\|postgres> <SQL>` | Run a read-only SQL query |
| `/db-query:schema <mysql\|postgres> [table]` | Inspect table schema, columns, and indexes |
| `/db-query:tables [mysql\|postgres\|all]` | List all tables with row counts |

## Features

- Asks for `DATABASE_URL` (MySQL) or `PAYMENT_DATABASE_URL` (PostgreSQL) before querying
- Tests connection before running any queries
- Shows the SQL statement executed with every query result
- Safety guards block all write operations (INSERT, UPDATE, DELETE, DROP, etc.)
- Auto-detects Docker service names and remaps to localhost ports

## Supported databases

- **MySQL** (main) -- core application database (users, invoices, bids, companies, etc.)
- **PostgreSQL** (payment) -- payment service database (payment events, projections, financial data)

## Skill

The `db-query` skill activates automatically when you ask about database data, e.g. "check if bid 953171 is deleted" or "how many deleted bids in 2024".

## Examples

```
/db-query:query mysql SELECT * FROM users LIMIT 5
/db-query:schema mysql invoices
/db-query:tables all
```
