#!/bin/bash
# Localhost-only PostgreSQL write executor
# Usage: write-postgres.sh "DB_URL" "SQL_QUERY"
# DB_URL format: postgresql://user:password@host:port/database

set -euo pipefail

if [ $# -lt 2 ] || [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 \"DB_URL\" \"SQL_QUERY\"" >&2
  exit 1
fi

DB_URL="$1"
SQL="$2"

# Parse the host from the URL for localhost validation
PG_REMAINDER="${DB_URL#*://}"
PG_HOSTPORTDB="${PG_REMAINDER#*@}"
PG_HOSTPORT="${PG_HOSTPORTDB%%/*}"
PG_HOST="${PG_HOSTPORT%%:*}"
PG_PORT="${PG_HOSTPORT#*:}"
if [ "$PG_PORT" = "$PG_HOST" ]; then
  PG_PORT="5432"
fi

# --- LOCALHOST-ONLY ENFORCEMENT ---
RESOLVED_HOST="$PG_HOST"
PG_URL="$DB_URL"

# Auto-detect Docker service name and remap to localhost
if [ ! -f /.dockerenv ] && command -v docker &>/dev/null; then
  CONTAINER_ID=$(docker ps --format '{{.ID}} {{.Names}}' 2>/dev/null | grep -i "$PG_HOST" | head -1 | awk '{print $1}' || true)
  if [ -n "$CONTAINER_ID" ]; then
    MAPPED=$(docker port "$CONTAINER_ID" "$PG_PORT" 2>/dev/null | head -1)
    if [ -n "$MAPPED" ]; then
      RESOLVED_HOST="127.0.0.1"
      MAPPED_PORT="${MAPPED##*:}"
      PG_USERPASS="${PG_REMAINDER%%@*}"
      PG_DBPARAMS="${PG_HOSTPORTDB#*/}"
      PG_PROTO="${PG_URL%%://*}"
      PG_URL="${PG_PROTO}://${PG_USERPASS}@127.0.0.1:${MAPPED_PORT}/${PG_DBPARAMS}"
    fi
  fi
fi

# Reject non-localhost connections
if [[ "$RESOLVED_HOST" != "localhost" && "$RESOLVED_HOST" != "127.0.0.1" && "$RESOLVED_HOST" != "::1" ]]; then
  echo "ERROR: Write operations are only allowed on localhost connections." >&2
  echo "Host '$RESOLVED_HOST' is not localhost. Refusing to execute write query on remote database." >&2
  exit 1
fi

# --- WRITE OPERATION WHITELIST ---
# Normalize: uppercase, collapse whitespace, strip comments
NORMALIZED=$(echo "$SQL" | sed 's/--.*$//g' | tr '\n' ' ' | sed 's|/\*.*\*/||g' | tr '[:lower:]' '[:upper:]' | sed 's/[[:space:]]\+/ /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# Only allow INSERT statements
if ! echo "$NORMALIZED" | grep -qEi "^[[:space:]]*INSERT[[:space:]]" ; then
  echo "ERROR: Only INSERT statements are allowed through the write command." >&2
  echo "For UPDATE, DELETE, or schema changes, use the database client directly." >&2
  exit 1
fi

# Block dangerous operations that could be embedded
DANGEROUS_KEYWORDS="DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE[[:space:]]+(DATABASE|USER|SCHEMA)|DELETE|UPDATE[[:space:]]+.+[[:space:]]+SET|COPY"
if echo "$NORMALIZED" | grep -qEi "(${DANGEROUS_KEYWORDS})" ; then
  echo "ERROR: Dangerous operations detected in query. Only simple INSERT statements are allowed." >&2
  exit 1
fi

psql "$PG_URL" -c "$SQL" 2>&1
