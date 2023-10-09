help:
	@echo "Usage:"
	@echo "\_ make deps"
	@echo "\_ make build"
	@echo "\_ make deploy"
	@echo "\_ make init"
	@echo "\_ make start"
	@echo "\_ make stop"
	@echo "\_ make upgrade"
	@echo "\_ make deploy-env"
	@echo "\_ make push_dags"
	@echo "\_ make enable_dags"
	@echo "\_ make test"
	@echo "\_ make docker-network"
	@echo "\_ make logs"
	@echo "\_ make ps"
	@echo "\_ make info"
	@echo "\_ make clean"

topdir := $(shell pwd)
build_dir := $(topdir)/build

export WORKSPACE=$(topdir)/workspace
include install.env

docker-network:
	@echo "creating docker network: $(BOT_NETWORK_NAME)..."
	docker network inspect $(BOT_NETWORK_NAME) >/dev/null 2>&1 || docker network create $(BOT_NETWORK_NAME)

prepare-env:
	@echo "**************************************************************"
	@echo "* Dependency building..."
	@echo "**************************************************************"
	@echo "topdir: $(topdir)"
	@echo "creating building folder: $(build_dir)"
	@echo "WORKSPACE: $(WORKSPACE)"
	mkdir -p $(build_dir)
	mkdir -p $(WORKSPACE)
	chmod -R 777 $(WORKSPACE)
	@echo "creating environment files..."
	if [ ! -f $(build_dir)/.env ]; then \
		cp .env.template $(build_dir)/.env; \
		echo "HOSTNAME=`hostname`" >> $(build_dir)/.env; \
	fi
	chmod -R 777 $(build_dir)


# High-level execution order:
# deps -> build -> deploy -> init -> start
deps: prepare-env docker-network

build:
	cd docker && make build topdir=$(topdir)

build-nocache:
	cd docker && make build-nocache topdir=$(topdir)

deploy-airflow:
	cd docker && make deploy topdir=$(topdir) build_dir=$(build_dir)

deploy-env:
	cp $(build_dir)/.env $(BOT_HOME)/src

deploy: deploy-airflow deploy-env

init: deploy-env
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
	# cd docker && docker-compose run airflow-init-user
	cd docker && docker-compose run airflow-cli airflow dags trigger journal_daily

upgrade:
	@echo "###########################"
	@echo "[ops] Upgrading started"
	@echo "###########################"
	cd docker && make upgrade topdir=$(topdir)
	sleep 10
	@echo "###########################"
	@echo "[ops] Upgrading completed"
	@echo "###########################"

.PHONY: deps build deploy deploy-env init start stop logs clean push_dags
.PHONY: test upgrade enable_dags info ps help prepare-env docker-network
