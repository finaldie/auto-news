help:
	@echo "Usage:"
	@echo "\_ make start"
	@echo "\_ make stop"
	@echo "\_ make logs"
	@echo "\_ make clean"

topdir := $(shell pwd)
build_dir := $(topdir)/build

include $(build_dir)/install.env

docker-network:
	@echo "creating docker network for bot..."
ifeq ($(shell docker network ls -f name=$(BOT_NETWORK_NAME) -q | wc -l), 0)
	docker network create $(BOT_NETWORK_NAME)
else
	@echo "docker network $(BOT_NETWORK_NAME) already exist, skip"
endif

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

deploy-airflow:
	cd docker && make deploy topdir=$(topdir) build_dir=$(build_dir)

deploy-obsidian:
	cd docker && make deploy-obsidian obsidian_dir=$(obsidian_dir)

deploy-env:
	cp $(build_dir)/.env $(BOT_HOME)/src

deploy: deploy-airflow deploy-env

init:
	cd docker && make init topdir=$(topdir)

start: docker-network
	cd docker && make start topdir=$(topdir)

stop:
	cd docker && make stop topdir=$(topdir)

logs:
	cd docker && make logs topdir=$(topdir)

ps:
	cd docker && make ps topdir=$(topdir)

clean:
	docker system prune -f
	docker volume prune

info:
	cd docker && make info topdir=$(topdir)

enable_dags:
	cd docker && make enable_dags topdir=$(topdir)

push_dags:
	cd docker && make push_dags topdir=$(topdir)

test:
	cd docker && docker-compose run airflow-init-user 

.PHONY: deps build deploy deploy-env init start stop logs clean push_dags
