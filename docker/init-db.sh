#!/bin/bash
set -e

# This runs as the postgres user on container first start.
# Creates both dev and test databases.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE listingjet_test;
    GRANT ALL PRIVILEGES ON DATABASE listingjet_test TO $POSTGRES_USER;
EOSQL

echo "Created listingjet_test database"
