include $(topdir)/.Makefile.env

AIRFLOW_HOME ?= $(WORKSPACE)/airflow
BOT_HOME := $(AIRFLOW_HOME)/run/auto-news

help:
	@echo "deploy|init|start|stop"

deploy-code:
	echo "Deploying code ..."
	mkdir -p $(AIRFLOW_HOME)
	if [ ! -d $(BOT_HOME) ]; then \
		mkdir -p $(AIRFLOW_HOME)/run; \
		cp -r $(topdir) $(BOT_HOME); \
	fi
	cd $(BOT_HOME) && rm -rf build
	echo "Deploying code done"

# Airflow operations
# - The init steps: in venv, install.sh -> init-airflow -> push_dag
# - Then go to airflow home, start web and scheduler
deploy-airflow: deploy-code
	@echo "Assembling airflow ..."
	mkdir -p $(AIRFLOW_HOME)
	cd $(AIRFLOW_HOME) && mkdir -p dags logs plugins run data
	@echo "Airflow deployment finished"

post-deploy:

init-airflow:
	docker compose up airflow-init

# Platform targets
build:
	docker compose build

deploy: deploy-airflow post-deploy

init: init-airflow push_dags


start:
	docker-compose up -d


stop:
	docker-compose down

logs:
	docker-compose logs -f


push_dags:
	test -d $(AIRFLOW_HOME)/dags || mkdir -p $(AIRFLOW_HOME)/dags
	cd dags && cp *.py $(AIRFLOW_HOME)/dags


.PHONY: help deploy init start stop
.PHONY: init-airflow post-deploy deploy-code
