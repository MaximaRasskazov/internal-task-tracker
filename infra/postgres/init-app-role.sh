#!/bin/sh
set -eu

# psql variables quote the password as an SQL literal; never echo secrets.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=ON_ERROR_STOP=1 --set=runtime_password="$APP_DB_PASSWORD" <<'SQL'
CREATE ROLE tracker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'runtime_password';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE tracker TO tracker;
GRANT USAGE ON SCHEMA public TO tracker;
ALTER DEFAULT PRIVILEGES FOR ROLE tracker_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tracker;
ALTER DEFAULT PRIVILEGES FOR ROLE tracker_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO tracker;
SQL
