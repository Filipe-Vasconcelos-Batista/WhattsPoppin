#!/usr/bin/env bash
# Faz um pedido federado assinado de um servidor de dev a outro (ou a qualquer
# domínio) e mostra a resposta - para testar a identidade dos servidores:
#   backend/dev/federation-ping.sh a localhost:8002    -> o servidor A pinga o B
#   backend/dev/federation-ping.sh b localhost:8001    -> o servidor B pinga o A
# O primeiro argumento é quem envia (usa o .env e a chave desse servidor); o
# segundo é o destino, que tem de estar a correr (dev/federation.sh).
set -euo pipefail

server="${1:?uso: backend/dev/federation-ping.sh a|b <domínio[:porta]>}"
destination="${2:?uso: backend/dev/federation-ping.sh a|b <domínio[:porta]>}"
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
exec python -m app.federation.ping "$destination"
