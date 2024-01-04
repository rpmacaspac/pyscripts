
import boto3, botocore
import re
import time, datetime
import sys
import json, pprint
import os
import log_collector

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
        'family': "",
        'revision': ""
}


def get_cluster_env(env):
        response = client.list_clusters()
        clusters = response["clusterArns"]

        # get env
        for i in range(len(clusters)):
                # cluster = clusters[i].split("/")[1]
                cluster = clusters[i]
                
                if env == "1":
                        cluster_fin['cur_env'] = "latest"
                        filter = re.compile(r'latest$')
                        filter.search(cluster)
                        if (filter.search(cluster)):
                                filtered_cluster.append(cluster)

                elif env == "2":
                        cluster_fin['cur_env'] = "stage"
                        filter = re.compile(r'stage$')
                        filter.search(cluster)
                        if (filter.search(cluster)):
                                filtered_cluster.append(cluster)

                elif env == "3":
                        cluster_fin['cur_env'] = "load"
                        filter = re.compile(r'load$')
                        filter.search(cluster)
                        if (filter.search(cluster)):
                                filtered_cluster.append(cluster)

                elif env == "4":
                        cluster_fin['cur_env'] = "prod"
                        filter = re.compile(r'prod$')
                        filter.search(cluster)
                        if (filter.search(cluster)):
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


def describe_service():
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

        current = (f"\n#######################################\n"
        f"ServiceName: {style.BOLD}{response["services"][0]["serviceName"]}{style.RESET}\n"
        f"Status: {style.GREEN}{response["services"][0]["status"]}{style.RESET}\n"
        f"TaskDefinition: {style.UNDERLINE}{response["services"][0]["taskDefinition"].split("/")[1]}{style.RESET}\n"
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

def prep_env():
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

def prep():
        try:
                prep_env()
                describe_service()
                list_task()
        except ValueError:
                print("Wrong input. Exiting..")
                sys.exit()

def update_option():


        print('Update Service Task Definition\n')
        try:
                update_task_definition()
        except botocore.exceptions.ClientError:
                print('Invalid task definition version!\nExiting..')
                sys.exit()
        
def update_task_definition():

        print(f'Current Task Definition: {style.UNDERLINE}{cluster_td['family']}:{cluster_td['revision']}{style.RESET}')
        task_definition = input("Task definition version: ")
        # print('Task definition: revision')
        # list_of_td = response['taskDefinitionArns']
        # for i in range(5):
        #         print(list_of_td[i].split("/")[1])

        enter = input("Press ENTER to continue...")
        if enter != '':
                sys.exit()
        print(f"\n{dt} Updating task definition to {cluster_td['family']}:{task_definition}")


        client.update_service(
                cluster = cluster_fin['cur_cluster'],
                service = cluster_fin['cur_service'],
                taskDefinition = f"{cluster_td['family']}:{task_definition}"
        )

        log_collector.get_log(cluster_fin['cur_cluster'], cluster_fin['cur_service'])
        log_collector.clear_cache()


def start():
        global restart
        while True:
                print("ECS Actions\n1. Service Restart\n2. Deploy Task Definition")
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


        else:
                exit
        
        if restart == "y":
                restart_option()
                print(f"\nService Restart...{style.GREEN}OK{style.RESET}")
                return
        if restart == "n":
                update_option()
                print(f"\nDeployment...{style.GREEN}COMPLETED{style.RESET}")
                return




if __name__ == "__main__":
        try:
                start()
        except KeyboardInterrupt:
                sys.exit()

        except botocore.exceptions.ClientError:
                print('The security token included in the request is expired')

#### 
# Rolling restart working - passed test with correct input only
# Update TD - TBD
# Input Validation - In-Progress
                        # Restart the service?(y/n):
                                # onwards
# Catching ctrl+C - TBD
# Bug
##      logding latest cluster - fixed
                ## which environment on hkdl-apps-dev
                ## region not defined - fixed - added on credentials file(profile hkdl-apps-dev)
        # service name not consistent with console - eg. ma-scheduler
        # capture - there is current/ongoing deployment - running count,desired count and status message - or get last deployment = completed

## Actions
# Service Restart
        # add MANUAL STOP/START
                # for manual stop start -> capture desired task and auto scaling task
        # add input argument for user

# Update TD - done
# Update Image
        # Update image version and change it
        # Capture the new TD
# FEATURES
        # search and replace image tags -deadline TBD
                # to add cpu and mem update
        # add: reduce no. of task
        # create:
                # dynamic counter using kwargs depending on number of task - not used
        # usage info
        # option to continue and deploy after search and replace
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
	