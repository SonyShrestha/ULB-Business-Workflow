from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.email_operator import EmailOperator
from datetime import datetime, timedelta
import re

import os

current_file_directory = os.path.dirname(os.path.abspath(__file__))


# Define default_args dictionary
default_args = {
    'owner': 'aayush paudel',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Instantiate the DAG
dag = DAG(
    'process_web_log',
    default_args=default_args,
    description='DAG to process web logs daily',
    schedule_interval=timedelta(days=1),  # Run the DAG daily
)

## Define the task to scan for log file
scan_for_log_task = BashOperator(
    task_id='scan_for_log',
    bash_command=f'if [ -e {os.path.join(current_file_directory, "the_log", "log.txt")} ]; then echo "Log file found"; else echo "Log file not found"; exit 1; fi',
    dag=dag,
)





# Define the function to extract IP addresses from the log file
def extract_ip_addresses(**kwargs):
    log_file_path = os.path.join(current_file_directory, "the_log", "log.txt")
    output_file_path = os.path.join(current_file_directory,"output" ,"extracted_data.txt")

    # Regular expression to match an IP address in the log entry
    ip_address_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)')

    # Open the log file for reading
    with open(log_file_path, 'r') as log_file:
        # Extract IP addresses using the regular expression
        ip_addresses = [match.group(1) for line in log_file for match in ip_address_pattern.finditer(line)]

    # Write the extracted IP addresses to the output file
    with open(output_file_path, 'w') as output_file:
        for ip_address in ip_addresses:
            output_file.write(ip_address + '\n')

# Create the PythonOperator task for extracting data
extract_data_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_ip_addresses,
    provide_context=True,
    dag=dag,
)


# Task to transform data
def transform_data(**kwargs):
    input_file_path = os.path.join(current_file_directory,"output" ,"extracted_data.txt")
    output_file_path = os.path.join(current_file_directory,"output" ,"transformed_data.txt")
    ip_to_filter = "198.46.149.143"

    # Open the input file for reading
    with open(input_file_path, 'r') as input_file:
        # Filter out occurrences of the specified IP address
        filtered_lines = [line.strip() for line in input_file if line.strip() != ip_to_filter]

    # Write the filtered data to the output file
    with open(output_file_path, 'w') as output_file:
        for line in filtered_lines:
            output_file.write(line + '\n')

# Task to transform data
transform_data_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    provide_context=True,
    dag=dag,
)


# Task to load data (archive the file)
load_data_task = BashOperator(
    task_id='load_data',
    bash_command=f'tar -cf {os.path.join(current_file_directory,"weblog.tar")} {os.path.join(current_file_directory,"output" ,"transformed_data.txt")}',
    dag=dag,
)



# Task to send an email
email_task = EmailOperator(
    task_id='send_email',
    to='paudelaayus@gmail.com',  # Replace with the recipient's email address
    subject='Airflow DAG Execution Notification',
    html_content='The Airflow DAG has been executed successfully!',
    dag=dag,
)

# Set the task dependencies within the DAG
scan_for_log_task >> extract_data_task >> transform_data_task >> load_data_task >> email_task
#extract_data_task >> process_web_log_task
#scan_for_log_task

if __name__ == "__main__":
    dag.cli()
