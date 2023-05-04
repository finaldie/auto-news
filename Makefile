help:
	@echo "Usage:"
	@echo "\_ make start"
	@echo "\_ make stop"
	@echo "\_ make logs"
	@echo "\_ make clean"

topdir := $(shell pwd)
build_dir := $(topdir)/build

-include .Makefile.env
-include $(build_dir)/install.env

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
	cp $(topdir)/install.env $(build_dir)/
	echo "export HOSTNAME=`hostname`" >> $(build_dir)/install.env
	chmod -R 777 $(build_dir)


# High-level execution order:
# deps -> build -> deploy -> init -> start
deps: prepare-env docker-network

build:
	cd docker && make build

deploy-env:
	cp $(build_dir)/install.env $(WORKSPACE)/

deploy: deploy-env
	cd docker && make deploy

init:
	cd docker && make init

start:
	cd docker && make start

stop:
	cd docker && make stop

logs:
	cd docker && make logs

clean:
	docker system prune -f

push_dags:
	cd docker && make push_dags
