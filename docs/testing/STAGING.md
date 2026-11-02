# Staging

The staging project is local. It does not use the development volume. No host is selected.

docker compose --env-file .env.staging -p paperpilot-staging up -d --wait
docker compose --env-file .env.staging -p paperpilot-staging down -v
/health ok
/v1/health ok
volume: paperpilot-staging-pgdata
host: none selected
web: not in this compose
research: unreviewed
staging ok
