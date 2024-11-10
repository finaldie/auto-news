namespace ?= auto-news

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
	@echo "\_ make helm-repo-update"
	@echo "\_ make k8s-env-create"
	@echo "\_ make k8s-namespace-create"
	@echo "\_ make k8s-secret-create"
	@echo "\_ make k8s-docker-build repo=xxx tag=x.y.z"
	@echo "\_ make k8s-docker-push repo=xxx tag=x.y.z"
	@echo "\_ make k8s-helm-install"
	@echo "\_ make k8s-airflow-dags-enable"
	@echo ""
	@echo "=== ArgoCD deployment ==="
	@echo "\_ make k8s-argocd-install"
	@echo "\_ make k8s-airflow-dags-enable"
	@echo ""
	@echo "=== k8s port-fowarding ==="
	@echo "Airflow: 'kubectl port-forward service/auto-news-webserver 8080:8080 --namespace ${namespace} --address=0.0.0.0'"
	@echo "Milvus : 'kubectl port-forward service/auto-news-milvus-attu -n ${namespace} 9100:3001 --address=0.0.0.0'"
	@echo "Adminer: 'kubectl port-forward service/auto-news-adminer -n ${namespace} 8070:8080 --address=0.0.0.0'"


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
	if [ ! -f $(build_dir)/.env.k8s ]; then \
		cp .env.template.k8s $(build_dir)/.env.k8s; \
	fi
	chmod -R 777 $(build_dir)


# High-level execution order:
# deps -> build -> deploy -> init -> start
deps: prepare-env
# deps: docker-network

repo ?= finaldie/auto-news
tag ?= 0.9.15

build:
	cd docker && make build repo=$(repo) tag=$(tag) topdir=$(topdir)

build-nocache:
	cd docker && make build-nocache repo=$(repo) tag=$(tag) topdir=$(topdir)

push:
	cd docker && make push repo=$(repo) tag=$(tag)

deploy-airflow:
	cd docker && make deploy topdir=$(topdir) build_dir=$(build_dir)

deploy-env:
	cp $(build_dir)/.env $(BOT_HOME)/src

deploy: deploy-airflow

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
	docker volume prune -f

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
# -include build/.env.k8s

TIMEOUT ?= 10m0s

# steps to deploy to k8s:
# make helm-repo-update
# make k8s-env-create
# make k8s-namespace-create
# make k8s-secret-create
# [optional] make k8s-docker-build repo=xxx tag=1.0.0
# [optional] make k8s-docker-push repo=xxx tag=1.0.0
# make k8s-helm-install
# make k8s-airflow-dags-enable

helm-repo-update:
	helm repo add bitnami https://charts.bitnami.com/bitnami
	helm repo add zilliztech https://zilliztech.github.io/milvus-helm
	helm repo add apache-airflow https://airflow.apache.org
	helm repo add cetic https://cetic.github.io/helm-charts
	helm repo update

k8s-namespace-create:
	-kubectl create namespace ${namespace}

k8s-env-create:
	@echo "**Create env file for k8s**"
	mkdir -p $(build_dir)
	if [ ! -f $(build_dir)/.env.k8s ]; then \
		cp .env.template.k8s $(build_dir)/.env.k8s; \
	fi
	@echo "Review and adjust $(build_dir)/.env.k8s if needed"

k8s-secret-create:
	@echo "**Create airflow secret (namespace: ${namespace})**"
	-kubectl create secret generic airflow-secrets \
	-n ${namespace} \
	--from-env-file=build/.env.k8s

k8s-secret-delete:
	@echo "**Deleting airflow secret (namespace: ${namespace}) ...**"
	-kubectl delete secret \
		--ignore-not-found=true \
		-n ${namespace} \
		airflow-secrets

# k8s-docker-build repo=xxx tag=1.0.0
k8s-docker-build:
	cd docker && make build repo=${repo} tag=${tag} topdir=$(topdir)

# k8s-docker-push repo=xxx tag=1.0.0
k8s-docker-push:
	cd docker && make push repo=${repo} tag=${tag}

k8s-helm-install:
	cd ./helm && helm dependency build
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

k8s-airflow-dags-enable:
	@echo "Airflow DAGs unpausing..."
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags unpause news_pulling
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags unpause sync_dist
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags unpause collection_weekly
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags unpause journal_daily
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags unpause action
	@echo "Airflow DAGs unpausing finished"

airflow-dags-disable:
	@echo "Airflow DAGs pausing..."
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags pause news_pulling
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags pause sync_dist
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags pause collection_weekly
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags pause journal_daily
	kubectl exec -n ${namespace} auto-news-worker-0 -- airflow dags pause action
	@echo "Airflow DAGs pausing finished"

k8s-argocd-install:
	@echo "ArgoCD: Installing Auto-News argocd helm chart..."
	helm upgrade \
		--install \
		--debug \
		--namespace=${namespace} \
		--create-namespace \
		--timeout=${TIMEOUT} \
		--wait=true \
		argocd-apps-auto-news \
		./argocd
	@echo "ArgoCD: Auto-News argocd helm chart installation finished, goto ArgoCD dashboard to check the service deployment status"

# Notes: uninstall argocd helm chart won't uninstall the auto-news
# services, to uninstall auto-news, click 'Delete' button from ArgoCD
# dashboard
k8s-argocd-uninstall:
	@echo "ArgoCD uninstallation ..."
	helm uninstall \
		--ignore-not-found \
		--wait=true \
		--namespace=${namespace} \
		--debug \
		argocd-apps-auto-news


.PHONY: deps build deploy deploy-env init start stop logs clean push_dags
.PHONY: test upgrade enable_dags info ps help prepare-env docker-network
.PHONY: k8s-docker-build k8s-docker-push
