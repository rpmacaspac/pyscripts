import boto3
import sys

session = boto3.Session(profile_name='personal')
client = session.client('ecs')
events = ""
cur_event_id = ""
stable_event_id = ""
desired_count = 0
running_count = 0
event_current = ""
prev_event_id = 0
status = ""
status_msg = "has reached a steady state."

def clear_cache():
    global events, cur_event_id, stable_event_id, desired_count, running_count, event_current, prev_event_id, status
    events = None
    cur_event_id = None
    stable_event_id = None
    desired_count = None
    running_count = None
    event_current = None
    prev_event_id = None
    status = None

def collect_event(cur_cluster, cur_service):
    global events, desired_count, running_count
    response = client.describe_services(
        cluster=cur_cluster,
        services=[
            cur_service
        ]
    )

    events = response['services'][0]['events']
    desired_count = response['services'][0]['desiredCount']
    running_count = response['services'][0]['runningCount']

def get_current_event():
        global event_current, status, cur_event, cur_event_id
        cur_event = str(f'{events[0]['createdAt']} {events[0]['id']}')
        cur_event_id = cur_event.split(" ")[2]
        event_current = f'{events[0]['createdAt']} {events[0]['message']}'
        status = event_current.split(")")[1].strip()
        return cur_event_id, status


def get_log(cur_cluster, cur_service):
    global status_msg, stable_event_id
    collect_event(cur_cluster, cur_service)
    initial_event_id, initial_status = get_current_event()


    if initial_status == status_msg:
        stable_event_id = initial_event_id

    while True:
        global cur_event_id, prev_event_id, events, cur_event
        

        collect_event(cur_cluster, cur_service)
        cur_event_id, status = get_current_event()

        if "completed" in str(status_msg):
            print(event_current)
            continue

        if initial_event_id == cur_event_id and initial_status == status_msg:
            continue

        if not prev_event_id:
            print(event_current)
            prev_event_id = cur_event_id
           # prev_event_id = stable_event_id

        if cur_event_id != prev_event_id:
            if status == status_msg:
                this_event_current = f'{events[1]['createdAt']} {events[1]['message']}'
                if prev_event_id != str(f'{events[1]['createdAt']} {events[1]['id']}'):
                    print(this_event_current)

            print(event_current)
            prev_event_id = cur_event_id
            cur_event_id = None
            continue

        #Ending with steady state logging
        if status == status_msg and cur_event_id != stable_event_id and desired_count == running_count:
            break

if __name__ == "__main__":
    session = boto3.Session(profile_name='personal')
    client = session.client('ecs')
    
    try:
        cur_cluster = "arn:aws:ecs:ap-southeast-1:851303023089:cluster/my-cluster-latest"
        cur_service = "arn:aws:ecs:ap-southeast-1:851303023089:service/my-cluster-latest/nginx-latest"
        get_log(cur_cluster, cur_service)
    except KeyboardInterrupt:
        sys.exit()

### For improvement
            # Capture simultaneous logging - done