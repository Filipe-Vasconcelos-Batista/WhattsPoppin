#!/usr/bin/env bash
set -euo pipefail

usage="uso: backend/dev/federation-ping.sh a|b <domínio[:porta]> [MÉTODO CAMINHO]"
server="${1:?$usage}"
destination="${2:?$usage}"
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
exec python -m app.federation.ping "${@:2}"
