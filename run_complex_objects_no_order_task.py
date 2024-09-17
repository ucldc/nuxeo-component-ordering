import argparse

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
                    "command": command
                }
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