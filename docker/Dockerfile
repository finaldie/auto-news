FROM apache/airflow:2.8.4-python3.11

# keep them same as docker-compose volume path
VOLUME /opt/airflow
WORKDIR /opt/airflow

ENV WORKDIR=/opt/airflow
ENV PYTHONUNBUFFERED=1

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
    tree \
    ffmpeg \
  '; \
  apt-get update && apt-get install -y --no-install-recommends \
    $deps \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /root/.cache/*

# create a soft link ~/airflow -> /opt/airflow
# create auto-news folders
RUN set -ex; \
  ln -snf /opt/airflow ~/airflow \
  && mkdir -p /opt/airflow/run/auto-news/src \
  && chmod -R 777 /opt/airflow/run/auto-news/src

# switch to airflow user in order to install python packages
USER airflow

# create a soft link ~/airflow -> /opt/airflow
# create a symbol link for airflow user as well
RUN set -ex; \
  ln -snf /opt/airflow ~/airflow

# Install deps
COPY docker/requirements.txt .

RUN set -ex; \
  pip install --no-cache-dir -r requirements.txt \
  && rm -rf ~/.cache/pip

# Install DAGs
COPY dags/ /opt/airflow/dags/

# Install user code
COPY ./src /opt/airflow/run/auto-news/src
