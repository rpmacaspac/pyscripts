import boto3
import copy
import os
import sys

def describe_task_definition(ecs_client, task_definition_arn):
    response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
    return response['taskDefinition']

def get_old_smtp_credentials(task_definition):
    old_smtp_user = None
    old_smtp_pass = None
    smtp_user_key = None
    smtp_pass_key = None
    for container in task_definition['containerDefinitions']:
        for environment in container.get('environment', []):
            key = environment.get('name', '').lower()
            value = environment.get('value', '')
            if 'smtp' in key or 'mail' in key:
                if 'user' in key or 'username' in key:
                    old_smtp_user = value
                    smtp_user_key = key
                elif 'pass' in key or 'password' in key:
                    old_smtp_pass = value
                    smtp_pass_key = key
    return old_smtp_user, old_smtp_pass, smtp_user_key, smtp_pass_key

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

    )
    new_task_definition_arn = response['taskDefinition']['taskDefinitionArn']
    return new_task_definition_arn

if __name__ == "__main__":
    try:
        account = 'default'
        session = boto3.Session(profile_name=account)
        client = session.client('ecs')

        # edit to become dynamic or input user
        current_td = "arn:aws:ecs:ap-northeast-1:876496569223:task-definition/tkt-adm-svc-hk:473" # added to ecs-action script as current_td['arn']

        # Describe existing task definition
        task_definition = describe_task_definition(client, current_td)
        task_definition_arn = task_definition['taskDefinitionArn']

        # Get old SMTP credentials from environment variables in task definition
        old_smtp_user, old_smtp_pass, smtp_user_key, smtp_pass_key = get_old_smtp_credentials(task_definition)

        if not old_smtp_user or not old_smtp_pass:
            print("Old SMTP credentials not found in task definition environment variables.")
            sys.exit(1)

        print(f"Old SMTP username ('{smtp_user_key}'): {old_smtp_user}")
        print(f"Old SMTP password ('{smtp_pass_key}'): {old_smtp_pass}")

        new_smtp_user = input("Enter new SMTP username: ")
        new_smtp_pass = input("Enter new SMTP password: ")

        if not new_smtp_user or not new_smtp_pass:
            print("New SMTP credentials not provided.")
            sys.exit(1)

        if len(old_smtp_user) != len(new_smtp_user) or len(old_smtp_pass) != len(new_smtp_pass):
            print("Error: Old and new SMTP credentials must have the same length.")
            sys.exit(1)

        # Update all image tag in the task definition
        updated_task_definition = update_strings(task_definition, old_smtp_user, new_smtp_user)
        updated_task_definition = update_strings(updated_task_definition, old_smtp_pass, new_smtp_pass)

        # Register a new task definition with the updated image tag
        new_task_definition_arn = register_new_task_definition(client, updated_task_definition)

        print(f"New task definition registered: {new_task_definition_arn}")
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)
