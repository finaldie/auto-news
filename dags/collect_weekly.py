from datetime import datetime, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
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


def should_run(**kwargs):
    """
    The pipeline should only runs on Saturday

    :param dict kwargs: Context
    :return: Id of the task to run
    :rtype: str
    """
    next_exec_date = kwargs['next_execution_date']
    force_to_run = kwargs["dag_run"].conf.setdefault("force_to_run", False)

    print('---- weekday: {}, force_to_run: {}, context {}'.format(next_exec_date.weekday(), force_to_run, kwargs))

    if force_to_run:
        return "start"

    # check weekday is Saturday, aka weekday() == 5
    if next_exec_date.weekday() == 5:
        return "start"
    else:
        return "finish"


with DAG(
        'collection_weekly',
        default_args=default_args,
        max_active_runs=1,
        description='Collect weekly best content. config: {'
                    ', "targets": "notion", "dedup": true, "min-rating": 4, '
                    '"force_to_run": true}',
        # schedule_interval=timedelta(minutes=60),
        schedule_interval="30 2 */1 * *",  # At 02:30 everyday
        # schedule_interval=None,
        start_date=days_ago(1),
        tags=['NewsBot'],
) as dag:
    br = BranchPythonOperator(
        task_id='condition',
        python_callable=should_run,
        dag=dag,
    )

    t1 = BashOperator(
        task_id='start',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_start.py --start {{ ds }} --prefix=./run',
    )

    t2 = BashOperator(
        task_id='prepare',
        bash_command='mkdir -p ~/airflow/data/collect/{{ run_id }}',
    )

    t3 = BashOperator(
        task_id='pull',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_collect.py '
                     '--start {{ ds }} '
                     '--prefix=./run '
                     '--run-id={{ run_id }} '
                     '--job-id={{ ti.job_id }} '
                     '--data-folder=data/collect '
                     '--collection-type=weekly '
                     '--min-rating={{ dag_run.conf.setdefault("min-rating", 4) }} '
    )

    t4 = BashOperator(
        task_id='save',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_publish.py '
                     '--start {{ ds }} '
                     '--prefix=./run '
                     '--run-id={{ run_id }} '
                     '--job-id={{ ti.job_id }} '
                     '--data-folder=data/collect '
                     '--targets={{ dag_run.conf.setdefault("targets", "notion") }} '
                     '--collection-type=weekly '
                     '--min-rating={{ dag_run.conf.setdefault("publishing-min-rating", 4.5) }} '
    )

    t5 = BashOperator(
        task_id='finish',
        depends_on_past=False,
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_end.py '
                     '--start {{ ds }} '
                     '--prefix=./run ',
    )

    br >> t1 >> t2 >> t3 >> t4 >> t5
    br >> t5
