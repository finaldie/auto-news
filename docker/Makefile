
help:
	@echo "deploy|init|start|stop"

deploy-code:
	echo "Deploying code ..."
	mkdir -p $(AIRFLOW_PROJ_DIR)
	if [ ! -d $(BOT_HOME) ]; then \
		mkdir -p $(AIRFLOW_PROJ_DIR)/run; \
		cd $(AIRFLOW_PROJ_DIR)/run && git clone https://github.com/finaldie/auto-news.git; \
	fi
	echo "Deploying code done"

# Airflow operations
# - The init steps: in venv, install.sh -> init-airflow -> push_dag
# - Then go to airflow home, start web and scheduler
deploy-airflow: deploy-code
	@echo "Assembling Airflow ..."
	mkdir -p $(AIRFLOW_PROJ_DIR)
	cd $(AIRFLOW_PROJ_DIR) && mkdir -p dags logs plugins run data
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
	docker compose up airflow-init

# Platform targets
build:
	docker compose build

deploy: deploy-airflow deploy-postgres deploy-redis deploy-mysql deploy-milvus
deploy: post-deploy


init: push_dags

start-services:
	docker-compose up -d

start: start-services
	@echo ""
	@echo "Services started, links:"
	@echo "- Airflow: http://`hostname`:8080"
	@echo "- Milvus: http://`hostname`:9100"
	@echo "- Adminer: http://`hostname`:8070"

stop:
	docker-compose down

logs:
	docker-compose logs -n 1000

ps:
	docker-compose ps

info:
	docker-compose run airflow-cli airflow info
	docker-compose run airflow-cli airflow dags list

enable_dags:
	docker-compose run airflow-cli airflow dags unpause news_pulling
	docker-compose run airflow-cli airflow dags unpause sync_dist
	docker-compose run airflow-cli airflow dags unpause collection_weekly

push_dags:
	test -d $(AIRFLOW_PROJ_DIR)/dags || mkdir -p $(AIRFLOW_PROJ_DIR)/dags
	cd $(topdir)/dags && cp *.py $(AIRFLOW_PROJ_DIR)/dags

.PHONY: help deploy init start stop
.PHONY: init-airflow post-deploy deploy-code logs info ps push_dags
.PHONY: enable_dags deploy-postgres
