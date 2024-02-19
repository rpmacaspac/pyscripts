import boto3
import copy
import sys,re


def describe_task_definition(ecs_client, task_definition_arn):
    response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
    return response['taskDefinition']

def update_strings(obj, old_smtp, new_smtp):
    if isinstance(obj, str):
        return obj.replace(old_smtp, new_smtp)
    elif isinstance(obj, list):
        return [update_strings(item, old_smtp, new_smtp) for item in obj]
    elif isinstance(obj, dict):
        updated_obj = copy.deepcopy(obj)
        for key, value in updated_obj.items():
            updated_obj[key] = update_strings(value, old_smtp, new_smtp)
        return updated_obj
    else:
        return obj


def register_new_task_definition(ecs_client, task_definition):
    response = ecs_client.register_task_definition(
        family = task_definition['family'],
        containerDefinitions=task_definition['containerDefinitions'],
        volumes = task_definition.get('volumes'),
        cpu = task_definition.get('cpu'),
        memory = task_definition.get('memory')
    )
    new_task_definition_arn = response['taskDefinition']['taskDefinitionArn']
    return new_task_definition_arn



if __name__ == "__main__":
    account = 'default'
    session = boto3.Session(profile_name=account)
    client = session.client('ecs')
    ecr_client = boto3.client('ecr')

    # edit to become dynamic or input user
    current_td = "arn:aws:ecs:ap-northeast-1:876496569223:task-definition/ma-scheduler:421" # added to ecs-action script as current_td['arn']

    old_smtp_user = ""
    new_smtp_user = ""
    old_smtp_pass = ""
    new_stmp_pass = ""

    # Describe existing task definition
    task_definition = describe_task_definition(client, current_td)
    task_definition_arn = task_definition['taskDefinitionArn']


    # Update all image tag in the task definition
    updated_task_definition = update_strings(task_definition, old_smtp_user, new_smtp_user)

    # Register a new task definition with the updated image tag
    new_task_definition_arn = register_new_task_definition(client, updated_task_definition)

    print(f"New task definition registered: {new_task_definition_arn}")
