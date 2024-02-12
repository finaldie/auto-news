from datetime import timedelta

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
    'upgrade',
    default_args=default_args,
    max_active_runs=1,
    description='Version upgrading config: {}',
    # schedule_interval=timedelta(minutes=60),
    # schedule_interval="1 * * * *",  # At minute 01 every hour
    schedule_interval=None,
    # schedule_interval='@hourly',
    start_date=days_ago(1),
    tags=['NewsBot'],
) as dag:

    t0 = BashOperator(
        task_id='git_pull',
        bash_command='cd ~/airflow/run/auto-news && git pull && git log -1',
    )

    t6 = BashOperator(
        task_id='finish',
        depends_on_past=False,
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_end.py '
        '--start {{ ds }} '
        '--prefix=./run ',
    )

    t0 >> t6
