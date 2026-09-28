#!/usr/bin/env bash
# Arranca um dos servidores de dev (a ou b) para testar a federação:
#   backend/dev/run-server.sh a    -> localhost:8001
#   backend/dev/run-server.sh b    -> localhost:8002
set -euo pipefail

server="${1:?uso: backend/dev/run-server.sh a|b}"
dev_dir="$(cd "$(dirname "$0")" && pwd)"
backend_dir="$(dirname "$dev_dir")"
env_file="$dev_dir/server-$server.env"

if [[ ! -f "$env_file" ]]; then
  echo "Não existe $env_file - usa 'a' ou 'b'" >&2
  exit 1
fi

set -a
source "$backend_dir/../.env"
source "$env_file"
set +a

cd "$backend_dir"
source .venv/bin/activate
pw_migrate migrate --directory migrations --database "$DATABASE_URL"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
