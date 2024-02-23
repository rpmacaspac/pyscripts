
import boto3, botocore
import re
import time, datetime
import sys
import json, pprint
import os
import log_collector, update_td

class style():
  RED = '\033[31m'
  GREEN = '\033[38;5;10m'
  BLUE = '\033[34m'
  RESET = '\033[0m'
  YELLOW = '\033[93m'
  PURPLE = '\033[95m'
  CYAN = '\033[96m'
  DARKCYAN = '\033[36m'
  UNDERLINE = '\033[4m'
  BOLD = '\033[1m'


account = 'personal'
session = boto3.Session(profile_name=account)
client = session.client('ecs')
ecr_client = session.client('ecr')
#client = boto3.client('ecs')
dt = datetime.datetime.today()
seconds_now = dt.timestamp
filtered_cluster = []
list_services = []
cur_rolling_restart = ""
restart = ""



cluster_fin = {
        'cur_cluster': "",
        'cur_env': "",
        'cur_service': "",
        'cur_tasks': [],
        'cur_task_definition': ""
}

cluster_td = {
        'arn': "",
        'family': "",
        'revision': "",
        'image_tag': "",
        'image_arn': "",
        'task_definition' : ""
}

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

def get_cluster_service(cluster):

        cluster_fin['cur_cluster'] = str(filtered_cluster[cluster-1])

        response = client.list_services(
                cluster = cluster_fin['cur_cluster']
        )
        services = response["serviceArns"]

        for i in range(len(services)):
                list_services.append(services[i])

def get_service(service):
        cluster_fin['cur_service'] = str(list_services[service-1])


def describe_service(cluster_td):
        response = client.describe_services(
        cluster = cluster_fin['cur_cluster'],
        services = [
                cluster_fin['cur_service']
                ]
        )
        cluster_fin['cur_running_count'] = response["services"][0]["runningCount"]
        cluster_fin['cur_desired_count'] = response["services"][0]["desiredCount"]
        cluster_td['family'] = response["services"][0]["taskDefinition"].split("/")[1].split(":")[0]
        cluster_td['revision'] = response["services"][0]["taskDefinition"].split("/")[1].split(":")[1]
        cluster_td['arn'] = response["services"][0]["taskDefinition"]

        cluster_td['task_definition'] = describe_task_definition(client, cluster_td['arn'])
        task_definition = cluster_td['task_definition']
        container_definition = task_definition['containerDefinitions']
        cluster_td['image_tag'] = container_definition[0]['image'].split(':')[1]
        cluster_td['image_arn'] = container_definition[0]['image']

        current = (f"\n#######################################\n"
        f"ServiceName: {style.BOLD}{response["services"][0]["serviceName"]}{style.RESET}\n"
        f"Status: {style.GREEN}{response["services"][0]["status"]}{style.RESET}\n"
        f"TaskDefinition: {style.UNDERLINE}{response["services"][0]["taskDefinition"].split("/")[1]}{style.RESET}\n"
        f"ImageTag: {cluster_td['image_tag']}\n"
        f"RunningCount: {style.GREEN}{response["services"][0]["runningCount"]}{style.RESET}\n"
        f"DesiredCount: {response["services"][0]["desiredCount"]}\n"
        "#######################################\n")
        print(f"\n{current}")


def list_task():
        response = client.list_tasks(
                cluster=cluster_fin['cur_cluster'],
                serviceName=cluster_fin['cur_service'],
                desiredStatus='RUNNING'
                )

        tasks = response["taskArns"]
        for i in range(len(tasks)):
                task = tasks[i]
                cluster_fin['cur_tasks'].append(task)

def stop_task(task):
        response = client.stop_task(
                cluster=cluster_fin['cur_cluster'],
                task=task,
                reason='Ecs service restart'
                )
        print(f"{dt} Stopping {task}")

def capture_log():
        log_collector.get_log(cluster_fin['cur_cluster'], cluster_fin['cur_service'])
        log_collector.clear_cache()

def rolling_restart():
        while cluster_fin['cur_tasks']:
                for i in range(int(cur_rolling_restart)):
                        stop_task(cluster_fin['cur_tasks'][0])
                        cluster_fin['cur_tasks'].remove(cluster_fin['cur_tasks'][0])
                capture_log()


def validate_rolling():
       
        while True:
                cur_rolling_restart = input("How many simultaneous task/s(eg. 1,2,4,8..): ")
                if int(cur_rolling_restart) > int(cluster_fin["cur_running_count"]):
                        print('Invalid!')
                        continue
                if int(cur_rolling_restart) % 2 == 0:
                        return cur_rolling_restart
                
                if int(cluster_fin["cur_running_count"]) != 0 and int(cur_rolling_restart) == 1:
                        return cur_rolling_restart

def restart_option():
        while True:
                if cluster_fin['cur_running_count'] == 0:
                        sys.exit()
                ans1 = input("Restart the service?(y/n): ")
                if ans1 == "y":
                        global restart, cur_rolling_restart
                        restart = "y"
                        while True:
                                ans2 = input("Rolling restart?(y/n): ")
                                if ans2 == "y":
                                        cur_rolling_restart = validate_rolling()
                                        if int(cur_rolling_restart) > int(len(cluster_fin['cur_tasks'])): 
                                                restart = "n"
                                                print("Exiting...\nRolling restart value is greater than running tasks!")
                                                return
                                        enter = input("Press ENTER to continue...")
                                        if enter == '':
                                                print(f"\n\nRestarting with rolling update {style.YELLOW}{cur_rolling_restart}{style.RESET}")
                                                rolling_restart()
                                                return
                                        
                                if ans2 == "n":
                                        enter = input("Press ENTER to continue...")
                                        if enter == '':
                                                print("Restarting all running tasks.")
                                                print("\nTasks:")
                                                for task in cluster_fin['cur_tasks']:
                                                        print(task)
                                                        print("\n\n")
                                                for i in range(len(cluster_fin['cur_tasks'])):
                                                        print("Function: stop_task")
                                                        stop_task(cluster_fin['cur_tasks'][i])
                                                        capture_log()
                                                        return
                                else:
                                        continue

                elif ans1 == "n":
                        restart = "n"
                        print('\nExiting...')
                        sys.exit()
                else:
                        continue

def prep_env(cluster_td):
        global list_services
        while True:
                print("1. latest \n2. stage\n3. load\n4. prod")
                env = input("Which environment: ")
                if env == '1' or env == '2' or env == '3' or env == '4':
                        break
        get_cluster_env(env)

        while True:
                for i in range(len(filtered_cluster)):
                        print(f"{i+1}. {filtered_cluster[i].split("/")[1]}")
                if not filtered_cluster:
                        print(filtered_cluster)
                        sys.exit()
                cluster = input("Which cluster: ")
                if int(cluster) <= len(filtered_cluster):
                        break

        get_cluster_service(int(cluster))

        while True:
                
                for i in range(len(list_services)):
                        print(f"{i+1}. {list_services[i].split("/")[-1]}")
                service = input("Which service: ")
                if int(service) <= len(list_services):
                        break
                
        get_service(int(service))

def update_option():

        print('Update Service Task Definition\n')
        update_task_definition()

        # For testing
        # try:
        #         update_task_definition()
        # except botocore.exceptions.ClientError: # bug: except an error(didn't catch because of this except block) but still continue to update td
        #         print('Invalid task definition version!\nExiting..')
        #         sys.exit()
        
def update_task_definition():
    print(f'Current Task Definition: {style.UNDERLINE}{cluster_td["family"]}:{cluster_td["revision"]}{style.RESET}')
    task_definition = input("Task definition version: ")

    enter = input("Press ENTER to continue...")
    if enter != '':
        sys.exit()

    if cluster_fin['cur_running_count'] == 0 and cluster_fin['cur_desired_count'] == 0:
        print("Service is not running. Update can't proceed.")
        sys.exit()

    print(f"\n{dt} Updating task definition to {cluster_td['family']}:{task_definition}")

    client.update_service(
        cluster=cluster_fin['cur_cluster'],
        service=cluster_fin['cur_service'],
        taskDefinition=f"{cluster_td['family']}:{task_definition}"
    )

    log_collector.get_log(cluster_fin['cur_cluster'], cluster_fin['cur_service'])
    log_collector.clear_cache()

def prep():
        try:
                prep_env(cluster_td)
                describe_service(cluster_td)
                list_task()
        except ValueError:
                print("Wrong input. Exiting..")
                sys.exit()

def describe_task_definition(ecs_client, task_definition):
    response = ecs_client.describe_task_definition(taskDefinition = task_definition)
    return response['taskDefinition']


def update_td_image_tag(cluster_td, client, update_td):
        new_image_tag = input('New Image Tag: ') ## must be user input
        old_image_tag = cluster_td['image_tag'] # currently existing in ecs-action script as revision


        # get the image arn before initializing the ecr_client, this will allow the region to be specified
        # repository_name = update_td.extract_repository_name(cluster_td['image_arn'])

        # if repository_name:
        try:
                # if not account == 'personal':
                #         ecr_client.describe_repositories(repositoryNames = [repository_name])


                update_td.validate_image_tag_format(old_image_tag,new_image_tag)

                # Update all image tag in the task definition
                updated_task_definition = update_td.update_strings(cluster_td['task_definition'], old_image_tag, new_image_tag)

                # Register a new task definition with the updated image tag
                new_task_definition_arn = update_td.register_new_task_definition(client, updated_task_definition)

                print(f"New task definition registered: {new_task_definition_arn}")


        except ecr_client.exceptions.RepositoryNotFoundException:
               # print(f"The Repository '{repository_name}' is not existing in the registry.")
                print(f"The Repository is not existing in the registry.")

def start():
        global restart
        while True:
                print("ECS Actions\n1. Service Restart\n2. Deploy Task Definition\n3. Update Image Tag")
                action = input("What would you like to do? ")
                if action == '1' or action == '2' or action == '3':
                        break

        prep()

        if action == "1":
                restart = "y"
                if not cluster_fin['cur_tasks']:
                        print("No task is running!\nExiting...")
                        sys.exit()
        if action == "2":
                restart = "n"
        
        if action == "3":
                restart = "n"

        else:
                exit
        
        if restart == "y":
                restart_option()
                print(f"\nService Restart...{style.GREEN}OK{style.RESET}")
                return
        if restart == "n" and action == "2":
                update_option()
                print(f"\nDeployment...{style.GREEN}COMPLETED{style.RESET}")
                return
        if restart == "n" and action == "3":
                update_td_image_tag(cluster_td, client, update_td)

if __name__ == "__main__":
        try:
                start()
        except KeyboardInterrupt:
                sys.exit()

        # except botocore.exceptions.ClientError:
        #         print('The security token included in the request is expired')

#### 
# Rolling restart working - passed test with correct input only
# Update TD - TBD
# Input Validation - Done
                        # Restart the service?(y/n):
                                # onwards
# Catching ctrl+C - TBD
# Bug
##      logding latest cluster - fixed
                ## which environment on hkdl-apps-dev
                ## region not defined - fixed - added on credentials file(profile hkdl-apps-dev)
        # service name not consistent with console - eg. ma-scheduler - fixed
        # capture - there is current/ongoing deployment - running count,desired count and status message - or get last deployment = completed

## Actions
# Service Restart
        # add MANUAL STOP/START
                # for manual stop start -> capture desired task and auto scaling task
        # add input argument for user

# Update TD - done
# Update Image Tag
        # Update image version and change it - done
        # Capture the new TD - done
                # highlight the TD revision number
# FEATURES
        # search and replace image tags - Done
                # to add cpu and mem update - ready
        # OPTIONAL
                # add: reduce no. of task
                # create:
                        # dynamic counter using kwargs depending on number of task - not used
        # usage info
        # option to continue and deploy after search and replace
        # capture - there is current/ongoing deployment - running count,desired count and status message - or get last deployment = completed

# Create a git repo - done on rpmacaspac
                



# Refactoring
                        # no time for this
                
                
# class Apps:
# 	def __init__(self) -> None:
# 		self.cluster
# 		self.service
# 		self.tasks
# 	def prep
# 		cluster = ""
# 		env
# 		list_clusters
# 			self.cluster = cluster
# 	def list_services
# 	def list_tasks
# 	def restart
# 	def update_td

# def main():
	
# 	input which env?
# 	input which cluster?
# 	input which service?
# 	input what action?
	