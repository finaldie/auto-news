help:
	@echo "Usage:"
	@echo "\_ make start"
	@echo "\_ make stop"
	@echo "\_ make logs"
	@echo "\_ make clean"

topdir := $(shell pwd)
build_dir := $(topdir)/build

include $(topdir)/install.env

docker-network:
	@echo "creating docker network for bot..."
	docker network create $(BOT_NETWORK_NAME)

prepare-env:
	@echo "**************************************************************"
	@echo "* Dependency building..."
	@echo "**************************************************************"
	@echo "topdir: $(topdir)"
	@echo "creating building folder: $(build_dir)"
	mkdir -p $(build_dir)
	mkdir -p $(WORKSPACE)
	chmod -R 777 $(WORKSPACE)
	@echo "creating environment files..."
	cp .env.template $(build_dir)/.env
	echo "HOSTNAME=`hostname`" >> $(build_dir)/.env
	chmod -R 777 $(build_dir)


# High-level execution order:
# deps -> build -> deploy -> init -> start
deps: prepare-env docker-network

build:
	cd docker && make build topdir=$(topdir)

deploy-env:
	cp $(build_dir)/.env $(WORKSPACE)/

deploy: deploy-env
	cd docker && make deploy topdir=$(topdir)

init:
	cd docker && make init topdir=$(topdir)

start:
	cd docker && make start topdir=$(topdir)

stop:
	cd docker && make stop topdir=$(topdir)

logs:
	cd docker && make logs topdir=$(topdir)

clean:
	docker system prune -f

push_dags:
	test -d $(AIRFLOW_PROJ_DIR)/dags || mkdir -p $(AIRFLOW_PROJ_DIR)/dags
	cd dags && cp *.py $(AIRFLOW_PROJ_DIR)/dags

.PHONY: deps build deploy deploy-env init start stop logs clean push_dags
