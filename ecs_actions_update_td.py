# To update an image tags for deployment update/upgrade

### flow
## Describe task definition
## Validate new image tag
## Search and replace string in json
## Register task definition
## Capture task definition number

import boto3
import copy
import sys

def describe_task_definition(ecs_client, task_definition_arn):
    response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
    return response['taskDefinition']

# def update_image_tag(task_definition, new_image_tag, old_image_tag):
#     container_definition = task_definition['containerDefinitions'][0]
#     image_ui = container_definition['image']

#     # Update existing image tag in container definition
#     new_image_uri = image_ui.rsplit(':', 1)[0] + f':{new_image_tag}'
#     container_definition['image'] = new_image_uri


# only usable for manual input 
def old_image_tag_exists(task_definition, old_image_tag):
    for container_definition in task_definition['containerDefinitions']:
        if 'image' in container_definition and old_image_tag in container_definition['image']:
            return True
        return False
    

def update_strings(obj, old_image_tag, new_image_tag):
    if isinstance(obj, str):
        return obj.replace(old_image_tag, new_image_tag)
    elif isinstance(obj, list):
        return [update_strings(item, old_image_tag, new_image_tag) for item in obj]
    elif isinstance(obj, dict):
        updated_obj = copy.deepcopy(obj)
        for key, value in updated_obj.items():
            updated_obj[key] = update_strings(value, old_image_tag, new_image_tag)
        return updated_obj
    else:
        return obj


def register_new_task_definition(ecs_client, task_definition):


    response = ecs_client.register_task_definition(
        family = task_definition['family'],
        containerDefinitions=task_definition['containerDefinitions'],
        volumes = task_definition.get('volumes'),
        # cpu = task_definition.get('cpu'),
        # memory = task_definition.get('memory')
    )
    new_task_definition_arn = response['taskDefinition']['taskDefinitionArn']

    return new_task_definition_arn

def validate_image_tag_format(old_image_tag, new_image_tag):
    
    # getting format of old and new
    old_tag_parts = old_image_tag.split('.')
    new_tag_parts = new_image_tag.split('.')

    if len(old_tag_parts) != len(new_tag_parts):
        print(f"Error: New image tag '{new_image_tag}' does not adhere to the old image tag '{old_image_tag}'.")
    
    # add: must be existing in ECR


if __name__ == "__main__":
    account = 'default'
    session = boto3.Session(profile_name=account)
    client = session.client('ecs')
    current_td = "arn:aws:ecs:ap-northeast-1:876496569223:task-definition/ma-scheduler:421" # added to ecs-action script as current_td['arn']
    new_image_tag = "2.0.0.20240102160420" ## must be user input
    old_image_tag = "2.0.0.20231227094445" # currently existing in ecs-action script as revision

    # Describe existing task definition
    task_definition = describe_task_definition(client, current_td)
    
    # Update Image tag in the task definition
    #update_image_tag(task_definition, new_image_tag, old_image_tag)
    
    # Check if old image tag exists in the task definition
    if not old_image_tag_exists(task_definition, old_image_tag):
        print(f"Error: Old image tag '{old_image_tag}' does not exist in the task definition.")
        sys.exit(1)

    # Update all image tag in the task definition
    updated_task_definition = update_strings(task_definition, old_image_tag, new_image_tag)

    # Register a new task definition with the updated image tag
    new_task_definition_arn = register_new_task_definition(client, updated_task_definition)



    print(f"New task definition registered: {new_task_definition_arn}")