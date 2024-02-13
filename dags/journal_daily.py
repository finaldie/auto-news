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


with DAG(
    'journal_daily',
    default_args=default_args,
    max_active_runs=1,
    description='config: {"sources": "Journal", "targets": "notion", "dedup": true}',
    # schedule_interval=timedelta(minutes=60),
    schedule_interval="30 3 */1 * *",  # At 03:30 UTC everyday
    # schedule_interval=None,
    start_date=days_ago(1),
    tags=['NewsBot'],
) as dag:

    t1 = BashOperator(
        task_id='start',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_start.py --start {{ ds }} --prefix=./run',
    )

    t2 = BashOperator(
        task_id='prepare',
        bash_command='mkdir -p ~/airflow/data/journal/{{ run_id }}',
    )

    t3 = BashOperator(
        task_id='pull',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_journal_pull.py '
        '--start {{ ds }} '
        '--prefix=./run '
        '--run-id={{ run_id }} '
        '--job-id={{ ti.job_id }} '
        '--data-folder=data/journal '
        '--sources={{ dag_run.conf.setdefault("sources", "Journal") }} '
    )

    t4 = BashOperator(
        task_id='save',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_journal_save.py '
        '--start {{ ds }} '
        '--prefix=./run '
        '--run-id={{ run_id }} '
        '--job-id={{ ti.job_id }} '
        '--data-folder=data/journal '
        '--sources={{ dag_run.conf.setdefault("sources", "Journal") }} '
        '--targets={{ dag_run.conf.setdefault("targets", "notion") }} '
    )

    t5 = BashOperator(
        task_id='finish',
        depends_on_past=False,
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_end.py '
        '--start {{ ds }} '
        '--prefix=./run ',
    )

    t1 >> t2 >> t3 >> t4 >> t5
