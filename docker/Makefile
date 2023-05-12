
help:
	@echo "deploy|init|start|stop"

deploy-code:
	echo "Deploying code ..."
	mkdir -p $(AIRFLOW_PROJ_DIR)
	if [ ! -d $(BOT_HOME) ]; then \
		mkdir -p $(AIRFLOW_PROJ_DIR)/run; \
		cp -r $(topdir) $(BOT_HOME); \
	fi
	cd $(BOT_HOME) && rm -rf build
	echo "Deploying code done"

# Airflow operations
# - The init steps: in venv, install.sh -> init-airflow -> push_dag
# - Then go to airflow home, start web and scheduler
deploy-airflow: deploy-code
	@echo "Assembling airflow ..."
	mkdir -p $(AIRFLOW_PROJ_DIR)
	cd $(AIRFLOW_PROJ_DIR) && mkdir -p dags logs plugins run data
	@echo "Airflow deployment finished"

deploy-redis:
	@echo "Assembling redis ..."
	mkdir -p $(REDIS_PROJ_DIR)/data
	@echo "Redis deployment finished"

deploy-mysql:
	@echo "Assembling mysql ..."
	mkdir -p $(MYSQL_PROJ_DIR)/data
	@echo "Mysql deployment finished"

post-deploy:

init-airflow:
	docker compose up airflow-init

# Platform targets
build:
	docker compose build

deploy: deploy-airflow deploy-redis deploy-mysql post-deploy


init: init-airflow push_dags


start:
	docker-compose up -d


stop:
	docker-compose down

logs:
	docker-compose logs -f

push_dags:
	test -d $(AIRFLOW_PROJ_DIR)/dags || mkdir -p $(AIRFLOW_PROJ_DIR)/dags
	cd $(topdir)/dags && cp *.py $(AIRFLOW_PROJ_DIR)/dags

.PHONY: help deploy init start stop
.PHONY: init-airflow post-deploy deploy-code
