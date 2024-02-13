from datetime import datetime, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': [''],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}

# Important Notes: This DAG must be executed before others, since it
# will create the new embedding table first, then other DAGs can be
# consumed later
with DAG(
        'sync_dist',
        default_args=default_args,
        max_active_runs=1,
        description='Sync content from ToRead. config: {"sources": "targets": "Milvus", '
                    '"dedup": true, '
                    '"min-rating": 4}',
        # schedule_interval=timedelta(minutes=60),
        # schedule_interval="1 * * * *",  # At minute 01 every hour
        # schedule_interval=None,
        schedule_interval='@hourly',
        start_date=days_ago(0, hour=1),
        tags=['NewsBot'],
) as dag:
    t1 = BashOperator(
        task_id='start',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_start.py --start {{ ds }} --prefix=./run',
    )

    t2 = BashOperator(
        task_id='prepare',
        bash_command='mkdir -p ~/airflow/data/sync/{{ ds }}/{{ run_id }}',
    )

    t3 = BashOperator(
        task_id='pull',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_sync.py '
                     '--start {{ ds }} '
                     '--prefix=./run '
                     '--run-id={{ run_id }} '
                     '--job-id={{ ti.job_id }} '
                     '--data-folder=data/sync/{{ ds }} '
    )

    t4 = BashOperator(
        task_id='save',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_dist.py '
                     '--start {{ ds }} '
                     '--prefix=./run '
                     '--run-id={{ run_id }} '
                     '--job-id={{ ti.job_id }} '
                     '--data-folder=data/sync '
                     '--targets={{ dag_run.conf.setdefault("targets", "Milvus") }} '
                     '--min-rating={{ dag_run.conf.setdefault("min-rating", 4) }} '
                     '--dedup={{ dag_run.conf.setdefault("dedup", True) }} '
    )

    t5 = BashOperator(
        task_id='clean',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_clean.py '
                     '--start {{ ds }} '
                     '--prefix=./run '
                     '--run-id={{ run_id }} '
                     '--job-id={{ ti.job_id }} '
                     '--milvus-retention-days={{ dag_run.conf.setdefault("--milvus-retention-days", 3) }} '
    )

    t6 = BashOperator(
        task_id='finish',
        depends_on_past=False,
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_end.py '
                     '--start {{ ds }} '
                     '--prefix=./run ',
    )

    t1 >> t2 >> t3 >> t4 >> t5 >> t6
