help:
	@echo "deploy|init|start|stop"

# Copy src to target workspace
deploy-code:
	echo "Deploying code ..."
	mkdir -p $(AIRFLOW_PROJ_DIR)
	mkdir -p $(BOT_HOME)/src;
	cp -r $(topdir)/src/*.py $(BOT_HOME)/src;
	echo "Deploying code done"

# Airflow operations
# - The init steps: in venv, install.sh -> init-airflow -> push_dag
# - Then go to airflow home, start web and scheduler
deploy-airflow:
	@echo "Assembling Airflow ..."
	mkdir -p $(AIRFLOW_PROJ_DIR)
	cd $(AIRFLOW_PROJ_DIR) && mkdir -p dags logs config plugins run data
	cd $(AIRFLOW_PROJ_DIR) && chmod 777 run/ data/
	@echo "Copy environment file ..."
	cp $(topdir)/build/.env $(AIRFLOW_PROJ_DIR)/config
	@echo "Airflow deployment finished"

deploy-postgres:
	@echo "Assembling Postgres ..."
	mkdir -p $(POSTGRES_PROJ_DIR)/data
	@echo "Postgres deployment finished"

deploy-redis:
	@echo "Assembling Redis ..."
	mkdir -p $(REDIS_PROJ_DIR)/data
	@echo "Redis deployment finished"

deploy-mysql:
	@echo "Assembling Mysql ..."
	mkdir -p $(MYSQL_PROJ_DIR)/data
	@echo "Mysql deployment finished"

deploy-milvus:
	@echo "Assembling Milvus ..."
	mkdir -p $(MILVUS_PROJ_DIR)/volumes
	@echo "Milvus deployment finished"

post-deploy:

init-airflow:
	docker compose --env-file ../build/.env up airflow-init

# Platform targets
# build repo=xxx tag=1.0.0
build:
	@echo "Building docker image, topdir: [$(topdir)]"
	docker build --pull --rm -t ${repo}:${tag} -f Dockerfile $(topdir)

# build repo=xxx tag=1.0.0
build-nocache:
	@echo "Building docker image (no-cache), topdir: [$(topdir)]"
	docker build --pull --no-cache --rm -t ${repo}:${tag} -f Dockerfile $(topdir)

# push repo=xxx tag=1.0.0
push:
	docker push ${repo}:${tag}

deploy: deploy-airflow deploy-postgres deploy-redis deploy-mysql deploy-milvus
deploy: post-deploy


init: push_dags copy_files

start-services:
	echo "Starting services with env file: $(topdir)/build/.env"
	docker compose --env-file $(topdir)/build/.env up -d

start: start-services
	@echo ""
	@echo "Services started, links:"
	@echo "- Airflow: http://`hostname`:8080"
	@echo "- Milvus: http://`hostname`:9100"
	@echo "- Adminer: http://`hostname`:8070"

stop:
	docker compose down

logs:
	docker compose logs -n 1000

ps:
	docker compose ps

info:
	docker compose run airflow-cli airflow info
	docker compose run airflow-cli airflow dags list

upgrade:
	docker compose run airflow-cli airflow dags trigger upgrade

enable_dags:
	docker compose run airflow-cli airflow dags unpause news_pulling
	docker compose run airflow-cli airflow dags unpause sync_dist
	docker compose run airflow-cli airflow dags unpause collection_weekly
	docker compose run airflow-cli airflow dags unpause upgrade
	docker compose run airflow-cli airflow dags unpause journal_daily

push_dags:
	test -d $(AIRFLOW_PROJ_DIR)/dags || mkdir -p $(AIRFLOW_PROJ_DIR)/dags
	cd $(topdir)/dags && cp *.py $(AIRFLOW_PROJ_DIR)/dags

copy_files:
	if [ -f requirements-local.txt ]; then \
		cp requirements-local.txt $(AIRFLOW_PROJ_DIR)/run/; \
	fi

.PHONY: help deploy init start stop
.PHONY: init-airflow post-deploy deploy-code logs info ps push_dags
.PHONY: enable_dags deploy-postgres copy_files
