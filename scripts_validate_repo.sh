#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"

export APP_ENV=test
export DATABASE_URL="sqlite+pysqlite:///./.tmp_validation.sqlite3"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="osint_neo4j_password"
export REDIS_URL="redis://localhost:6379/0"
export CORS_ORIGINS="http://localhost:3000,http://localhost:5173"

rm -f .tmp_validation.sqlite3

printf '\n--- python compile ---\n'
python3.11 -m compileall -q apps/api/app apps/api/tests
PY_COMPILE=$?

printf '\n--- import app.main ---\n'
PYTHONPATH=apps/api python3.11 scripts_validate_import.py
PY_IMPORT=$?

printf '\n--- pytest ---\n'
PYTHONPATH=apps/api pytest -q apps/api/tests
PY_TEST=$?

printf '\n--- frontend check ---\n'
pnpm run check
TS_CHECK=$?

printf '\n--- frontend build ---\n'
pnpm run build
FRONTEND_BUILD=$?

printf '\n--- summary ---\n'
printf 'python_compile=%s\npython_import=%s\npytest=%s\nfrontend_check=%s\nfrontend_build=%s\n' "$PY_COMPILE" "$PY_IMPORT" "$PY_TEST" "$TS_CHECK" "$FRONTEND_BUILD"

rm -f .tmp_validation.sqlite3

if [ "$PY_COMPILE" -ne 0 ] || [ "$PY_IMPORT" -ne 0 ] || [ "$PY_TEST" -ne 0 ] || [ "$TS_CHECK" -ne 0 ] || [ "$FRONTEND_BUILD" -ne 0 ]; then
  exit 1
fi
