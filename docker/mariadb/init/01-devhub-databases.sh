#!/bin/bash
# Runs once, when the MariaDB data volume is first initialized.
# Creates the dev and test databases with separate accounts so the test
# account can never read or modify development data.
# Sourced (not executed) by the entrypoint so docker_process_sql is available;
# keep it non-executable and do not change shell options here.

: "${DEVHUB_DEV_PASSWORD:?DEVHUB_DEV_PASSWORD is required}"
: "${DEVHUB_TEST_PASSWORD:?DEVHUB_TEST_PASSWORD is required}"

docker_process_sql <<-EOSQL
	CREATE DATABASE IF NOT EXISTS devhub_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci;
	CREATE DATABASE IF NOT EXISTS devhub_test CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci;

	CREATE USER IF NOT EXISTS 'devhub_dev'@'%' IDENTIFIED BY '${DEVHUB_DEV_PASSWORD}';
	CREATE USER IF NOT EXISTS 'devhub_test'@'%' IDENTIFIED BY '${DEVHUB_TEST_PASSWORD}';

	GRANT ALL PRIVILEGES ON devhub_dev.* TO 'devhub_dev'@'%';
	GRANT ALL PRIVILEGES ON devhub_test.* TO 'devhub_test'@'%';
	FLUSH PRIVILEGES;
EOSQL
