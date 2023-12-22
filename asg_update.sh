#!/usr/bin/env bash

[[ "${DEBUG}" == 'true' ]] && set -o xtrace # trace if debug is requested
PATH="/usr/local/bin:${PATH}"

## Log formatting
log_prefix() { echo "$(date +%Y-%m-%dT%H:%M:%S%z) $0:"; }
log_error()  { echo "$(log_prefix) [ERROR] $1" >&2; }
log(){
	if [[ "$LOG_LEVEL" != "ERROR" ]]; then
		echo "$(log_prefix) [INFO]  $1";
	fi
}

## This function centralizes error check and exits if issue
## usage
##    exit_if_error $? "Message to send to system.err"
function exit_if_error() {
  if [[ $1 != 0 ]]; then         # do nothing if error code is 0
    log_error "$2"
    exit "$1"
  fi
}

function create_new_launch_config() {

    log "Suspending ASG policies to not scale up during changes"
    aws --profile "$PROFILE" --region "$REGION" autoscaling suspend-processes --auto-scaling-group-name "$ASGGROUP" --scaling-processes "Launch" "Terminate"
    exit_if_error $? "Unable to suspend ASG"

    log "Creating backup"
    aws --profile "$PROFILE" --region "$REGION" autoscaling describe-launch-configurations --launch-configuration-name "$LAUNCHCONFIG"  > "$LAUNCHCONFIG"_bak.json
    exit_if_error $? "Unable to create backup of 'Launch configuration'"

    log "Decoding UserData from launchconfig"
    cat "$LAUNCHCONFIG"_bak.json | jq --raw-output '.LaunchConfigurations[].UserData' | base64 --decode > "$LAUNCHCONFIG"_userdata.txt
    #4
    log "Modify and update 'Launch configuration'"
    cat "$LAUNCHCONFIG"_bak.json | jq 'del(.LaunchConfigurations[].UserData) | del(.LaunchConfigurations[].CreatedTime) | del(.LaunchConfigurations[].LaunchConfigurationARN) | del(.LaunchConfigurations[].KernelId) | del(.LaunchConfigurations[].RamdiskId)| .LaunchConfigurations[].InstanceType = "instance_type" | .[] | .[]' > "$LAUNCHCONFIG".json
    exit_if_error $? "Unable to create new 'Launch configuration'"
    # 5
    log "Updating instance type"
    sed -i -e "s/instance_type/$INSTANCETYPE/g" "$LAUNCHCONFIG".json
    exit_if_error $? "Unable to edit volume size in 'Launch configuration'"
    #6
    log "Naming 'Launch configuration' to name inside the file"
    cat "$LAUNCHCONFIG".json | jq '(.LaunchConfigurationName += "_new")' > "$LAUNCHCONFIG"_new.json
    exit_if_error $? "Unable to name 'Launch configuration' file accurately"
    #7
    log "Creating duplicate of launch config and attaching to ASG"
    aws --profile "$PROFILE" --region "$REGION" autoscaling create-launch-configuration --cli-input-json file://"$LAUNCHCONFIG"_new.json --user-data file://"$LAUNCHCONFIG"_userdata.txt
    exit_if_error $? "Unable to create duplicate 'Launch configuration'"
    #8
    log "Updating ASG with new temp launch config"
    aws --profile "$PROFILE" --region "$REGION" autoscaling update-auto-scaling-group --auto-scaling-group-name "$ASGGROUP" --launch-configuration-name "$LAUNCHCONFIG"_new
    exit_if_error $? "Unable to update ASG with new temp 'Launch configuration'"
    #9
    log "Deleting existing launch config"
    aws --profile "$PROFILE" --region "$REGION" autoscaling  delete-launch-configuration --launch-configuration-name "$LAUNCHCONFIG"
    exit_if_error $? "Unable to delete existing 'Launch configuration'"
    #10
    log "Loading Launch config back with old name"
    aws --profile "$PROFILE" --region "$REGION" autoscaling create-launch-configuration --cli-input-json file://"$LAUNCHCONFIG".json --user-data file://"$LAUNCHCONFIG"_userdata.txt
    exit_if_error $? "Unable to load 'Launch configuration' back with old name"
    #11.
    log "Updating ASG Group with new launch"
    aws --profile "$PROFILE" --region "$REGION" autoscaling update-auto-scaling-group --auto-scaling-group-name "$ASGGROUP" --launch-configuration-name "$LAUNCHCONFIG"
    exit_if_error $? "Unable to updae ASG with new 'Launch configuration'"
    #12.
    log "Deleting uploaded launch config"
    aws --profile "$PROFILE" --region "$REGION" autoscaling  delete-launch-configuration --launch-configuration-name "$LAUNCHCONFIG"_new
    exit_if_error $? "Unable to delete existing 'Launch configuration'"
    #13.
    log "Removing ASG Suspensions"
    aws --profile "$PROFILE" --region "$REGION" autoscaling resume-processes --auto-scaling-group-name "$ASGGROUP" --scaling-processes "Launch" "Terminate"
    exit_if_error $? "Unable to remove ASG  suspensions"
    #14.
    log "Removing the json files"
    rm -rf "$LAUNCHCONFIG"_new.json "$LAUNCHCONFIG".json "$LAUNCHCONFIG".json-e
    exit_if_error $? "Unable to remove 'Launch configuration' json file"

    log "Completed"
}

function validate_parameters() {
    if [[ "$#" == 5 ]]; then
        PROFILE=$1
        REGION=$2
        ASGGROUP=$3
        LAUNCHCONFIG=$4
        INSTANCETYPE=$5
        log "Profile: $PROFILE" 
        log "Region: $REGION" 
        log "Autoscaling Group Name: $ASGGROUP" 
        log "Launch Configuration Name: $LAUNCHCONFIG" 
        log "New Instance Type: $INSTANCETYPE"
    else
        echo "All parameters not provided, please use command as below"
        echo "$0  AwsProfile Region AutoscalingGroup LaunchConfigurationName InstanceType"
        exit 1
    fi
}

main()
{
    validate_parameters "$@"
    create_new_launch_config
}

main "$@"