# Production security

The production project is local. Postgres has no host port. The docs routes are hidden. No host is selected.

docker compose --env-file .env.production -p paperpilot-production -f compose.yaml -f compose.production.yaml up -d --build --wait
docker compose --env-file .env.production -p paperpilot-production -f compose.yaml -f compose.production.yaml down -v
/health ok
/v1/health ok
/docs hidden
/redoc hidden
/openapi.json hidden
volume: paperpilot-production-pgdata
host: none selected
tls: none
firewall: none
password: none
administrators: none
research: unreviewed
production ok
