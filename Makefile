help:
	@echo "Usage:"
	@echo "=== Local deployment ==="
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
	@echo ""
	@echo "=== k8s deployment ==="
	@echo "\_ make k8s-env-create"
	@echo "\_ make k8s-secret-create"
	@echo "\_ make k8s-docker-build tag=x.y.z"
	@echo "\_ make k8s-docker-push tag=x.y.z"
	@echo "\_ make k8s-helm-install"


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

#######################################################################
# K8S / Helm
#######################################################################
-include build/.env

namespace ?= auto-news
TIMEOUT ?= 10m0s

# steps to deploy to k8s:
# make k8s-env-create
# make k8s-secret-create
# [optional] make k8s-docker-build tag=1.0.0
# make k8s-helm-install

k8s-env-create:
	@echo "***Create env file for k8s**"
	mkdir -p $(build_dir)
	if [ ! -f $(build_dir)/.env ]; then \
		cp .env.template $(build_dir)/.env; \
		echo "HOSTNAME=`hostname`" >> $(build_dir)/.env; \
	fi
	cat $(build_dir)/.env | grep -vE "NOTION_TOKEN|OPENAI_API_KEY|GOOGLE_API_KEY|REDDIT_CLIENT_ID|REDDIT_CLIENT_SECRET|AUTOGEN_GPT4_API_KEY|AUTOGEN_GPT3_API_KEY|TWITTER_API_KEY|TWITTER_API_KEY_SECRET|TWITTER_ACCESS_TOKEN|TWITTER_ACCESS_TOKEN_SECRET" >> $(build_dir)/.env.k8s
	@echo "**env file generated complete (secrets removed):**"
	@echo ""
	cat $(build_dir)/.env.k8s

k8s-secret-create:
	@echo "**Create airflow secret**"
	kubectl create secret generic airflow-secrets \
	-n ${namespace} \
  --from-literal=NOTION_TOKEN=$(NOTION_TOKEN) \
  --from-literal=OPENAI_API_KEY=$(OPENAI_API_KEY) \
  --from-literal=GOOGLE_API_KEY=$(GOOGLE_API_KEY) \
  --from-literal=REDDIT_CLIENT_ID=$(REDDIT_CLIENT_ID) \
  --from-literal=REDDIT_CLIENT_SECRET=$(REDDIT_CLIENT_SECRET) \
  --from-literal=AUTOGEN_GPT4_API_KEY=$(AUTOGEN_GPT4_API_KEY) \
  --from-literal=AUTOGEN_GPT3_API_KEY=$(AUTOGEN_GPT3_API_KEY) \
  --from-literal=TWITTER_API_KEY=$(TWITTER_API_KEY) \
  --from-literal=TWITTER_API_KEY_SECRET=$(TWITTER_API_KEY_SECRET) \
  --from-literal=TWITTER_ACCESS_TOKEN=$(TWITTER_ACCESS_TOKEN) \
  --from-literal=TWITTER_ACCESS_TOKEN_SECRET=$(TWITTER_ACCESS_TOKEN_SECRET)

k8s-secret-delete:
	@echo "**Delete airflow secret**"
	-kubectl delete secret \
		--ignore-not-found=true \
		-n ${namespace} \
		airflow-secrets

# k8s-docker-build tag=1.0.0
k8s-docker-build:
	cd docker && make build-k8s tag=${tag}

# k8s-docker-push tag=1.0.0
k8s-docker-push:
	cd docker && make push-k8s tag=${tag}

k8s-helm-install:
	helm upgrade \
     --install \
		 --debug \
     --namespace=${namespace} \
     --create-namespace \
     --timeout=${TIMEOUT} \
     --wait-for-jobs=true \
     auto-news \
     ./helm

k8s-helm-uninstall:
	helm uninstall \
		--ignore-not-found \
		--namespace=${namespace} \
		--wait=true \
		--debug \
		auto-news

.PHONY: deps build deploy deploy-env init start stop logs clean push_dags
.PHONY: test upgrade enable_dags info ps help prepare-env docker-network
.PHONY: k8s-docker-build k8s-docker-push
