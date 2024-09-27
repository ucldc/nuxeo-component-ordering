import os

import boto3

def main():
    command = ["python", "complex_objects_no_order.py"]

    # assume we're running this in the pad-dsc-admin account for now
    cluster = "nuxeo"
    subnets = ["subnet-b07689e9", "subnet-ee63cf99"] # Public subnets in the nuxeo VPC
    security_groups = ["sg-51064f34", "sg-e9460f8c"] # default security group for nuxeo VPC; nuxeo-app security group
    
    ecs_client = boto3.client("ecs")
    response = ecs_client.run_task(
        cluster = cluster,
        capacityProviderStrategy=[
            {
                "capacityProvider": "FARGATE",
                "weight": 1,
                "base": 1
            },
        ],
        taskDefinition = "nuxeo-component-ordering-task-definition",
        count = 1,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": security_groups,
                "assignPublicIp": "ENABLED"
            }
        },
        platformVersion="LATEST",
        overrides = {
            "containerOverrides": [
                {
                    "name": "nuxeo-component-ordering",
                    "command": command,
                    "environment": [
                        {
                            "name": "OUTPUT_URI",
                            "value": os.environ.get("OUTPUT_URI")
                        },
                        {
                            "name": "NUXEO_API_USER",
                            "value": os.environ.get("NUXEO_API_USER")
                        },
                        {
                            "name": "NUXEO_API_PASS",
                            "value": os.environ.get("NUXEO_API_PASS")
                        },
                        {
                            "name": "NUXEO_DB_NAME",
                            "value": os.environ.get("NUXEO_DB_NAME")
                        },
                        {
                            "name": "NUXEO_DB_USER",
                            "value": os.environ.get("NUXEO_DB_USER")
                        },
                        {
                            "name": "NUXEO_ELASTICSEARCH_ENDPOINT",
                            "value": os.environ.get("NUXEO_ELASTICSEARCH_ENDPOINT")
                        },
                        {
                            "name": "NUXEO_API_ENDPOINT",
                            "value": os.environ.get("NUXEO_API_ENDPOINT")
                        },
                        {
                            "name": "NUXEO_API_TOKEN",
                            "value": os.environ.get("NUXEO_API_TOKEN")
                        },
                        {
                            "name": "NUXEO_DB_HOST",
                            "value": os.environ.get("NUXEO_DB_HOST")
                        },
                        {
                            "name": "NUXEO_DB_PASS",
                            "value": os.environ.get("NUXEO_DB_PASS")
                        },
                        {
                            "name": "RIKOLTI_OPENSEARCH_ENDPOINT",
                            "value": os.environ.get("RIKOLTI_OPENSEARCH_ENDPOINT")
                        },
                    ],
                },
            ]
        },
        enableECSManagedTags=True,
        enableExecuteCommand=True
    )
    task_arn = [task['taskArn'] for task in response['tasks']][0]
    waiter = ecs_client.get_waiter('tasks_stopped')
    print(f"Started task in `{cluster}` cluster: {task_arn}")
    print(f"Waiting until task has stopped...")
    try:
        waiter.wait(
            cluster = cluster,
            tasks = [task_arn],
            WaiterConfig = {
                'Delay': 10,
                'MaxAttempts': 120
            }
        )
    except Exception as e:
        print('Task failed to finish running.', e)
    else:
        print('Task finished running.')

    response = ecs_client.describe_tasks(
        cluster = cluster,
        tasks = [task_arn],
        include = ['TAGS']
    )

    # import pprint
    # pprint.pp(response)
    for task in response['tasks']:
        for container in task['containers']:
            exit_code = container.get('exitCode')
            if exit_code != 0:
                print(f"ERROR: {container['name']} had non-zero exit code: {exit_code}")
                
    print("View python output in CloudWatch. Log group is named `nuxeo-component-ordering`.")

if __name__ == '__main__':
    (main())