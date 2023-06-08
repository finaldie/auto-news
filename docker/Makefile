
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
	@echo "Assembling Airflow ..."
	mkdir -p $(AIRFLOW_PROJ_DIR)
	cd $(AIRFLOW_PROJ_DIR) && mkdir -p dags logs plugins run data
	@echo "Airflow deployment finished"

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

deploy-obsidian:
	@echo "Create link for obsidian folder"
	ln -snf $(obsidian_dir) $(AIRFLOW_PROJ_DIR)/data/obsidian

post-deploy:

init-airflow:
	docker compose up airflow-init

# Platform targets
build:
	docker compose build

deploy: deploy-airflow deploy-redis deploy-mysql deploy-milvus
deploy: post-deploy


init: init-airflow push_dags


start:
	docker-compose up -d
	@echo ""
	@echo "Services started, links:"
	@echo "- Airflow: http://`hostname`:8080"
	@echo "- Milvus: http://`hostname`:9100"
	@echo "- Adminer: http://`hostname`:8070"

stop:
	docker-compose down

logs:
	docker-compose logs -f

ps:
	docker-compose ps

push_dags:
	test -d $(AIRFLOW_PROJ_DIR)/dags || mkdir -p $(AIRFLOW_PROJ_DIR)/dags
	cd $(topdir)/dags && cp *.py $(AIRFLOW_PROJ_DIR)/dags

.PHONY: help deploy init start stop
.PHONY: init-airflow post-deploy deploy-code
