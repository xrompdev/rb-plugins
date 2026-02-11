#!/bin/bash
# Read-only MySQL query executor
# Usage: query-mysql.sh "DB_URL" "SQL_QUERY"
# DB_URL format: mysql://user:password@host:port/database

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
BLOCKED_KEYWORDS="INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|RENAME|GRANT|REVOKE|LOCK|UNLOCK|LOAD|IMPORT|CALL|EXEC|EXECUTE|SET|FLUSH|RESET|PURGE|OPTIMIZE|REPAIR|ANALYZE[[:space:]]+TABLE|INTO[[:space:]]+OUTFILE|INTO[[:space:]]+DUMPFILE"

if echo "$NORMALIZED" | grep -qEi "^[[:space:]]*(${BLOCKED_KEYWORDS})" ; then
  echo "ERROR: Write/modify operations are not allowed. Only SELECT, SHOW, DESCRIBE, and EXPLAIN queries are permitted." >&2
  exit 1
fi

# Also block write keywords appearing anywhere (subqueries, CTEs)
if echo "$NORMALIZED" | grep -qEi "(INSERT[[:space:]]+INTO|UPDATE[[:space:]]+.+[[:space:]]+SET|DELETE[[:space:]]+FROM|DROP[[:space:]]+(TABLE|DATABASE|INDEX|VIEW)|ALTER[[:space:]]+(TABLE|DATABASE)|CREATE[[:space:]]+(TABLE|DATABASE|INDEX|VIEW)|TRUNCATE[[:space:]])" ; then
  echo "ERROR: Write/modify operations detected in query body. Only read operations are permitted." >&2
  exit 1
fi

# Whitelist: must start with a read operation
if ! echo "$NORMALIZED" | grep -qEi "^[[:space:]]*(SELECT|SHOW|DESCRIBE|DESC|EXPLAIN|WITH)" ; then
  echo "ERROR: Query must start with SELECT, SHOW, DESCRIBE, or EXPLAIN." >&2
  exit 1
fi

# Parse DB_URL: mysql://user:password@host:port/database
REMAINDER="${DB_URL#*://}"

USERPASS="${REMAINDER%%@*}"
HOSTPORTDB="${REMAINDER#*@}"

MYSQL_USER="${USERPASS%%:*}"
MYSQL_PASS="${USERPASS#*:}"

HOSTPORT="${HOSTPORTDB%%/*}"
MYSQL_DB="${HOSTPORTDB#*/}"
# Strip query params
MYSQL_DB="${MYSQL_DB%%\?*}"

MYSQL_HOST="${HOSTPORT%%:*}"
MYSQL_PORT="${HOSTPORT#*:}"
if [ "$MYSQL_PORT" = "$MYSQL_HOST" ]; then
  MYSQL_PORT="3306"
fi

# Auto-detect: if running outside Docker and host is a Docker service name,
# remap to 127.0.0.1 with the actual exposed port
if [ ! -f /.dockerenv ] && command -v docker &>/dev/null; then
  CONTAINER_ID=$(docker ps --format '{{.ID}} {{.Names}}' 2>/dev/null | grep -i "$MYSQL_HOST" | head -1 | awk '{print $1}' || true)
  if [ -n "$CONTAINER_ID" ]; then
    MAPPED=$(docker port "$CONTAINER_ID" "$MYSQL_PORT" 2>/dev/null | head -1)
    if [ -n "$MAPPED" ]; then
      MYSQL_HOST="127.0.0.1"
      MYSQL_PORT="${MAPPED##*:}"
    fi
  fi
fi

mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" "$MYSQL_DB" -e "$SQL" 2>&1
