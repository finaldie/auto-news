FROM apache/airflow:2.8.4-python3.11

# keep them same as docker-compose volume path
VOLUME /opt/airflow
WORKDIR /opt/airflow
ENV WORKDIR=/opt/airflow

# Switch to root in order to install system deps
USER root

# Install system deps
RUN set -ex; \
  deps=' \
    make \
    g++ \
    vim \
    net-tools \
    curl \
    wget \
    lsof \
    less \
    iputils-ping \
    telnet \
    procps \
    git \
    libgomp1 \
    jq \
    ffmpeg \
  '; \
  apt-get update && apt-get install -y --no-install-recommends \
    $deps \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /root/.cache/*

RUN set -ex; \
  git config --global --add safe.directory /opt/airflow/run/auto-news \
  && git config --global pull.ff only

# To fix redis bg save warning
RUN set -ex; \
  echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf

# Add ssh config (mount ~/.ssh/config will lead bad file owner issue)
# here we simply create one line .ssh/config, then we only need to
# mount id_rsa file into container
RUN set -ex; \
  mkdir -p ~/.ssh && echo "StrictHostKeyChecking=no" > ~/.ssh/config

# create a soft link ~/airflow -> /opt/airflow
RUN set -ex; \
  ln -snf /opt/airflow ~/airflow

# switch to airflow user in order to install python packages
USER airflow

RUN set -ex; \
  git config --global --add safe.directory /opt/airflow/run/auto-news \
  && git config --global pull.ff only

# create a soft link ~/airflow -> /opt/airflow
# create a symbol link for airflow user as well
RUN set -ex; \
  ln -snf /opt/airflow ~/airflow

ADD requirements.txt .

# Install deps
RUN set -ex; \
  pip install --no-cache-dir -r requirements.txt \
  && rm -rf ~/.cache/pip
