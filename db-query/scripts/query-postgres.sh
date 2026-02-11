#!/bin/bash
# Read-only PostgreSQL query executor
# Usage: query-postgres.sh "DB_URL" "SQL_QUERY"
# DB_URL format: postgresql://user:password@host:port/database

set -euo pipefail

if [ $# -lt 2 ] || [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 \"DB_URL\" \"SQL_QUERY\"" >&2
  exit 1
fi

DB_URL="$1"
SQL="$2"

# Normalize: uppercase, collapse whitespace, strip comments
NORMALIZED=$(echo "$SQL" | sed 's/--.*$//g' | tr '\n' ' ' | sed 's|/\*.*\*/||g' | tr '[:lower:]' '[:upper:]' | sed 's/[[:space:]]\+/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# Block any write/modify operations
BLOCKED_KEYWORDS="INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|RENAME|GRANT|REVOKE|LOCK|UNLOCK|LOAD|IMPORT|CALL|EXEC|EXECUTE|SET|FLUSH|RESET|PURGE|COPY|VACUUM|REINDEX|CLUSTER|REFRESH[[:space:]]+MATERIALIZED"

if echo "$NORMALIZED" | grep -qEi "^[[:space:]]*(${BLOCKED_KEYWORDS})" ; then
  echo "ERROR: Write/modify operations are not allowed. Only SELECT, SHOW, and EXPLAIN queries are permitted." >&2
  exit 1
fi

# Also block write keywords appearing anywhere (subqueries, CTEs)
if echo "$NORMALIZED" | grep -qEi "(INSERT[[:space:]]+INTO|UPDATE[[:space:]]+.+[[:space:]]+SET|DELETE[[:space:]]+FROM|DROP[[:space:]]+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)|ALTER[[:space:]]+(TABLE|DATABASE|SCHEMA)|CREATE[[:space:]]+(TABLE|DATABASE|INDEX|VIEW|SCHEMA)|TRUNCATE[[:space:]])" ; then
  echo "ERROR: Write/modify operations detected in query body. Only read operations are permitted." >&2
  exit 1
fi

# Whitelist: must start with a read operation
if ! echo "$NORMALIZED" | grep -qEi "^[[:space:]]*(SELECT|SHOW|EXPLAIN|WITH|\\\\D)" ; then
  echo "ERROR: Query must start with SELECT, SHOW, or EXPLAIN." >&2
  exit 1
fi

# Auto-detect: if running outside Docker and host is a Docker service name,
# remap to 127.0.0.1 with the actual exposed port
PG_URL="$DB_URL"

if [ ! -f /.dockerenv ] && command -v docker &>/dev/null; then
  PG_REMAINDER="${PG_URL#*://}"
  PG_HOSTPORTDB="${PG_REMAINDER#*@}"
  PG_HOSTPORT="${PG_HOSTPORTDB%%/*}"
  PG_HOST="${PG_HOSTPORT%%:*}"
  PG_PORT="${PG_HOSTPORT#*:}"
  if [ "$PG_PORT" = "$PG_HOST" ]; then
    PG_PORT="5432"
  fi

  CONTAINER_ID=$(docker ps --format '{{.ID}} {{.Names}}' 2>/dev/null | grep -i "$PG_HOST" | head -1 | awk '{print $1}' || true)
  if [ -n "$CONTAINER_ID" ]; then
    MAPPED=$(docker port "$CONTAINER_ID" "$PG_PORT" 2>/dev/null | head -1)
    if [ -n "$MAPPED" ]; then
      MAPPED_PORT="${MAPPED##*:}"
      PG_USERPASS="${PG_REMAINDER%%@*}"
      PG_DBPARAMS="${PG_HOSTPORTDB#*/}"
      PG_PROTO="${PG_URL%%://*}"
      PG_URL="${PG_PROTO}://${PG_USERPASS}@127.0.0.1:${MAPPED_PORT}/${PG_DBPARAMS}"
    fi
  fi
fi

psql "$PG_URL" -c "$SQL" 2>&1
