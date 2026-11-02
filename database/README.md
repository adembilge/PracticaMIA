PostgreSQL. FastAPI is the only writer. The tables are [models.py](../backend/models.py), as named in [SCHEMA.md](../docs/architecture/SCHEMA.md). [01-vector.sql](init/01-vector.sql) still only enables pgvector. From the repository root, `py -3 scripts/check_schema.py` runs [check_schema.py](../scripts/check_schema.py), which applies and rolls back the revision. [COMPONENTS.md](../docs/architecture/COMPONENTS.md)

The local service is [compose.yaml](../compose.yaml). It publishes PostgreSQL on 127.0.0.1 port 5432, keeps data in the volume paperpilot-pgdata, and enables pgvector from [01-vector.sql](init/01-vector.sql). That script does not create the application tables. Connection values are in [.env.example](../.env.example). There is no password.

From the repository root, `docker compose up -d --wait` starts it. Connect as user postgres to database paperpilot on 127.0.0.1 port 5432. `docker compose down` stops it and leaves the volume in place.

Staging names are in [.env.staging](../.env.staging). `py -3 scripts/check_staging.py` starts that project.
