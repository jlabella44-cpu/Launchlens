#!/bin/bash
set -e

# This runs as the postgres user on container first start.
# Creates both dev and test databases.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE launchlens_test;
    GRANT ALL PRIVILEGES ON DATABASE launchlens_test TO $POSTGRES_USER;
EOSQL

echo "Created launchlens_test database"
