import boto3
import sys
import datetime

import re

class Style:
    RED = '\033[31m'
    GREEN = '\033[38;5;10m'
    BLUE = '\033[34m'
    RESET = '\033[0m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    UNDERLINE = '\033[4m'
    BOLD = '\033[1m'

class ECSService:
    def __init__(self, client):
        self.client = client

    def describe_service(self, cluster, service):
        try:
            response = self.client.describe_services(
                cluster=cluster,
                services=[service]
            )
            return response["services"][0]
        except self.client.exceptions.ClientError as e:
            print(f"Failed to describe service: {e}")
            return None

    def list_tasks(self, cluster, service):
        try:
            response = self.client.list_tasks(
                cluster=cluster,
                serviceName=service,
                desiredStatus='RUNNING'
            )
            return response.get("taskArns", [])
        except self.client.exceptions.ClientError as e:
            print(f"Failed to list tasks: {e}")
            return []

    def stop_task(self, cluster, task):
        try:
            self.client.stop_task(
                cluster=cluster,
                task=task,
                reason='Ecs service restart'
            )
        except self.client.exceptions.ClientError as e:
            print(f"Failed to stop task: {e}")

class TaskDefinition:
    def __init__(self, ecs_client):
        self.ecs_client = ecs_client

    def describe_task_definition(self, task_definition):
        try:
            response = self.ecs_client.describe_task_definition(taskDefinition=task_definition)
            return response['taskDefinition']
        except self.ecs_client.exceptions.ClientError as e:
            print(f"Failed to describe task definition: {e}")
            return None

    def update_task_definition(self, cluster, service, new_task_definition):
        try:
            self.ecs_client.update_service(
                cluster=cluster,
                service=service,
                taskDefinition=new_task_definition
            )
        except self.ecs_client.exceptions.ClientError as e:
            print(f"Failed to update task definition: {e}")

class Cluster:
    def __init__(self, client):
        self.client = client

    def list_clusters(self):
        try:
            response = self.client.list_clusters()
            return response.get("clusterArns", [])
        except self.client.exceptions.ClientError as e:
            print(f"Failed to list clusters: {e}")
            return []

    def get_cluster_services(self, cluster):
        try:
            response = self.client.list_services(cluster=cluster)
            return response.get("serviceArns", [])
        except self.client.exceptions.ClientError as e:
            print(f"Failed to get cluster services: {e}")
            return []

account = 'personal'
session = boto3.Session(profile_name=account)
client = session.client('ecs')
ecr_client = session.client('ecr')

dt = datetime.datetime.today()

filtered_cluster = []  # Define filtered_cluster here
list_services = []  # Define list_services here
cluster_fin = {}  # Define cluster_fin dictionary
cluster_td = {}  # Define cluster_td dictionary
# Initialize cluster_td dictionary with placeholders
cluster_td = {'family': None, 'revision': None, 'arn': None, 'task_definition': None, 'image_tag': None, 'image_arn': None}


def get_cluster_env(env):
    clusters = Cluster(client).list_clusters()
    env_filters = {
        "1": "latest$",
        "2": "stage$",
        "3": "load$",
        "4": "prod$"
    }

    filter_pattern = re.compile(env_filters.get(env, ""))

    for cluster in clusters:
        match = filter_pattern.search(cluster)
        if match:
            filtered_cluster.append(cluster)

def prep_env(cluster_td):
    print("1. latest \n2. stage\n3. load\n4. prod")
    env = input("Which environment: ")
    if env in ['1', '2', '3', '4']:
        get_cluster_env(env)
    else:
        print("Invalid environment!")
        sys.exit()

    while True:
        for i, cluster in enumerate(filtered_cluster):
            print(f"{i+1}. {cluster.split('/')[1]}")
        if not filtered_cluster:
            print(filtered_cluster)
            sys.exit()
        cluster_index = input("Which cluster: ")
        if cluster_index.isdigit() and int(cluster_index) <= len(filtered_cluster):
            break

    cluster_services = Cluster(client).get_cluster_services(filtered_cluster[int(cluster_index) - 1])
    list_services.extend(cluster_services)

    while True:
        for i, service in enumerate(list_services):
            print(f"{i+1}. {service.split('/')[-1]}")
        service_index = input("Which service: ")
        if service_index.isdigit() and int(service_index) <= len(list_services):
            break

    return filtered_cluster[int(cluster_index) - 1], list_services[int(service_index) - 1]

def describe_service(cluster, service):
    service_info = ECSService(client).describe_service(cluster, service)
    if service_info:
        cluster_fin['cur_running_count'] = service_info.get("runningCount", 0)
        cluster_fin['cur_desired_count'] = service_info.get("desiredCount", 0)
        task_def = service_info["taskDefinition"]
        print("Task Definition:", task_def)  # Debugging statement
        try:
            family_revision = task_def.split("/")[1].split(":")
            cluster_td['family'] = family_revision[0]
            cluster_td['revision'] = family_revision[1]
        except IndexError:
            print("Unexpected format of task definition:", task_def)  # Error handling
            sys.exit(1)  # Exit the program with an error code
        cluster_td['arn'] = task_def
        cluster_td['task_definition'] = TaskDefinition(client).describe_task_definition(cluster_td['arn'])

        # Update cluster_td with current running task definition
        cluster_td['family'], cluster_td['revision'] = cluster_td['task_definition']['family'], cluster_td['task_definition']['revision']

        task_definition = cluster_td['task_definition']
        container_definition = task_definition['containerDefinitions']
        cluster_td['image_tag'] = container_definition[0]['image'].split(':')[1]
        cluster_td['image_arn'] = container_definition[0]['image']

        current_info = (f"\n#######################################\n"
                        f"ServiceName: {Style.BOLD}{service_info['serviceName']}{Style.RESET}\n"
                        f"Status: {Style.GREEN}{service_info['status']}{Style.RESET}\n"
                        f"TaskDefinition: {Style.UNDERLINE}{task_def.split('/')[1]}{Style.RESET}\n"
                        f"ImageTag: {cluster_td['image_tag']}\n"
                        f"RunningCount: {Style.GREEN}{service_info['runningCount']}{Style.RESET}\n"
                        f"DesiredCount: {service_info['desiredCount']}\n"
                        "#######################################\n")
        print(f"\n{current_info}")
    else:
        print("Failed to describe service.")
        sys.exit()





def list_task(cluster, service):
    return ECSService(client).list_tasks(cluster, service)

def stop_task(cluster, task):
    ECSService(client).stop_task(cluster, task)

def capture_log():
    log_collector.get_log(cluster_fin['cur_cluster'], cluster_fin['cur_service'])
    log_collector.clear_cache()

def rolling_restart(cur_rolling_restart):
    while cluster_fin['cur_tasks']:
        for _ in range(int(cur_rolling_restart)):
            stop_task(cluster_fin['cur_cluster'], cluster_fin['cur_tasks'][0])
            cluster_fin['cur_tasks'].pop(0)
        capture_log()


def validate_rolling():
    while True:
        cur_rolling_restart = input("How many simultaneous tasks (e.g., 1, 2, 4, 8..): ")
        if int(cur_rolling_restart) <= int(cluster_fin["cur_running_count"]):
            if int(cur_rolling_restart) % 2 == 0 or (int(cluster_fin["cur_running_count"]) != 0 and int(cur_rolling_restart) == 1):
                return cur_rolling_restart
        print('Invalid!')

def restart_option():
    if cluster_fin['cur_running_count'] == 0 and cluster_fin['cur_desired_count'] == 0:
        print("Service is not running. Restart can't proceed.")
        sys.exit()

    ans1 = input("Restart the service? (y/n): ")
    if ans1.lower() != "y":
        print('\nExiting...')
        sys.exit()

    ans2 = input("Rolling restart? (y/n): ")
    if ans2.lower() == "y":
        cur_rolling_restart = validate_rolling()
        if int(cur_rolling_restart) > len(cluster_fin['cur_tasks']):
            print("Exiting...\nRolling restart value is greater than running tasks!")
            return
        input("Press ENTER to continue...")
        print(f"\n\nRestarting with rolling update {Style.YELLOW}{cur_rolling_restart}{Style.RESET}")
        rolling_restart()
    else:
        input("Press ENTER to continue...")
        print("Restarting all running tasks.")
        print("\nTasks:")
        for task in cluster_fin['cur_tasks']:
            print(task)
            print("\n\n")
        for _ in range(len(cluster_fin['cur_tasks'])):
            print("Function: stop_task")
            stop_task(cluster_fin['cur_cluster'], cluster_fin['cur_tasks'][0])
            capture_log()

def update_option():
    print('Update Service Task Definition\n')
    update_task_definition()

def update_task_definition():
    print(f'Current Task Definition: {Style.UNDERLINE}{cluster_td['family']}:{cluster_td["revision"]}{Style.RESET}')
    task_definition = input("Task definition version: ")
    input("Press ENTER to continue...")
    print(f"\n{dt} Updating task definition to {cluster_td['family']}:{task_definition}")

    TaskDefinition(client).update_task_definition(cluster_fin['cur_cluster'], cluster_fin['cur_service'], f"{cluster_td['family']}:{task_definition}")

    log_collector.get_log(cluster_fin['cur_cluster'], cluster_fin['cur_service'])
    log_collector.clear_cache()

def start():
    while True:
        print("ECS Actions\n1. Service Restart\n2. Deploy Task Definition\n3. Update Image Tag")
        action = input("What would you like to do? ")
        if action in ['1', '2', '3']:
            break

    cluster, service = prep_env(cluster_td)
    cluster_fin['cur_cluster'] = cluster
    cluster_fin['cur_service'] = service

    if action == "1":
        describe_service(cluster, service)
        cluster_fin['cur_tasks'] = list_task(cluster, service)
        restart_option()
        print(f"\nService Restart...{Style.GREEN}OK{Style.RESET}")
    elif action == "2":
        update_option()
        print(f"\nDeployment...{Style.GREEN}COMPLETED{Style.RESET}")
    elif action == "3":
        # Add implementation for updating image tag
        pass

if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        sys.exit()
