#!/usr/bin/env bash
# Arranca o ambiente de federação em dev com um só comando:
#   servidor A  -> localhost:8001   cliente web A -> http://localhost:8091
#   servidor B  -> localhost:8002   cliente web B -> http://localhost:8092
# Ctrl+C pára tudo. Se um dos quatro processos morrer, os outros também param.
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/.." && pwd)"
postgres_container="whattspoppin-postgres"
server_b_db="whattspoppin_b"

set -a
source "$root_dir/.env"
set +a

echo "» Postgres"
docker compose -f "$root_dir/docker-compose.yml" up -d postgres
for _ in $(seq 30); do
  docker exec "$postgres_container" pg_isready -q -U "$POSTGRES_USER" && break
  sleep 1
done
docker exec "$postgres_container" pg_isready -q -U "$POSTGRES_USER" || {
  echo "O Postgres não ficou pronto em 30 s" >&2
  exit 1
}

db_exists="$(docker exec "$postgres_container" psql -U "$POSTGRES_USER" -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '$server_b_db'")"
if [[ "$db_exists" != "1" ]]; then
  echo "» A criar a BD $server_b_db (servidor B)"
  docker exec "$postgres_container" createdb -U "$POSTGRES_USER" "$server_b_db"
fi

echo "» Node (nvm)"
set +eu
source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
nvm use "$(cat "$root_dir/frontend/.nvmrc")" >/dev/null
nvm_status=$?
set -eu
if [[ $nvm_status -ne 0 ]]; then
  echo "O nvm não conseguiu ativar o Node de frontend/.nvmrc" >&2
  exit 1
fi

# Todos os processos ficam no grupo deste script: ao sair (Ctrl+C, erro, ou um
# deles a morrer) o kill 0 leva-os todos, e nenhum fica a ocupar portas.
trap 'trap - EXIT INT TERM; kill 0 2>/dev/null' EXIT INT TERM

export PYTHONUNBUFFERED=1

start() {
  local name="$1"
  shift
  ("$@" 2>&1 | sed -u "s/^/[$name] /") &
}

start "A    " "$root_dir/backend/dev/run-server.sh" a
start "B    " "$root_dir/backend/dev/run-server.sh" b
start "web-a" bash -c "cd '$root_dir/frontend' && npm run web:a"
start "web-b" bash -c "cd '$root_dir/frontend' && npm run web:b"

wait -n || true
echo "» Um dos processos terminou - a parar os restantes" >&2
