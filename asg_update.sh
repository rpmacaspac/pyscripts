#!/usr/bin/env bash


#Update
    #Added creating backup in cloud
    #Added optional for changing AmiID

# GLOBAL VARIABLE
export TODATE=""
TODATE="$(date +%Y%m%d)"
export BACKUP_NAME="_bak$TODATE"


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

    log "Creating backup JSON"
    aws --profile "$PROFILE" --region "$REGION" autoscaling describe-launch-configurations --launch-configuration-name "$LAUNCHCONFIG"  > "$LAUNCHCONFIG"_bak.json
    exit_if_error $? "Unable to create backup of 'Launch configuration'"

    # added for backup creation in cloud(for documentation purpose) although json backup was already created and saved locally
    log "Creating backup Launch Configuration"
    cat "$LAUNCHCONFIG"_bak.json | jq "del(.LaunchConfigurations[].UserData) | del(.LaunchConfigurations[].CreatedTime) | del(.LaunchConfigurations[].LaunchConfigurationARN) | del(.LaunchConfigurations[].KernelId) | del(.LaunchConfigurations[].RamdiskId) | .LaunchConfigurations[].LaunchConfigurationName += "$BACKUP_NAME" | .[] | .[]" > "$LAUNCHCONFIG$BACKUP_NAME".json
    exit_if_error $? "Unable to create backup 'Launch Configuration'"

    log "Decoding UserData from launchconfig"
    cat "$LAUNCHCONFIG"_bak.json | jq --raw-output '.LaunchConfigurations[].UserData' | base64 --decode > "$LAUNCHCONFIG"_userdata.txt

    ## added: 01/03/2023 for validating rundeck vm patching error
    log "Creating Backup of current running Launch Configuration"
    aws --profile "$PROFILE" --region "$REGION" autoscaling create-launch-configuration --cli-input-json file://"$LAUNCHCONFIG$BACKUP_NAME".json --user-data file://"$LAUNCHCONFIG"_userdata.txt
    log "Created Backup 'Launch Configuration': $(cat "$LAUNCHCONFIG$BACKUP_NAME".json | jq '(.LaunchConfigurationName)')"
    exit_if_error $? "Unable to create backup for currently running Launch Configuration"

    log "Modify and update 'Launch configuration'"
    if [[ -n "$AMIID" ]]; then
        cat "$LAUNCHCONFIG"_bak.json | jq 'del(.LaunchConfigurations[].UserData) | del(.LaunchConfigurations[].CreatedTime) | del(.LaunchConfigurations[].LaunchConfigurationARN) | del(.LaunchConfigurations[].KernelId) | del(.LaunchConfigurations[].RamdiskId)| .LaunchConfigurations[].InstanceType = "instance_type" | .LaunchConfigurations[].ImageId = "ami_id" | .[] | .[]' > "$LAUNCHCONFIG".json
        exit_if_error $? "Unable to create new 'Launch configuration'"
    else
        cat "$LAUNCHCONFIG"_bak.json | jq 'del(.LaunchConfigurations[].UserData) | del(.LaunchConfigurations[].CreatedTime) | del(.LaunchConfigurations[].LaunchConfigurationARN) | del(.LaunchConfigurations[].KernelId) | del(.LaunchConfigurations[].RamdiskId)| .LaunchConfigurations[].InstanceType = "instance_type" | .[] | .[]' > "$LAUNCHCONFIG".json
        exit_if_error $? "Unable to create new 'Launch configuration'"
    fi
    
    log "Updating instance type"
    if [[ -n "$AMIID" ]]; then
        sed -i -e "s/ami_id/$AMIID/g" "$LAUNCHCONFIG".json && sed -i -e "s/instance_type/$INSTANCETYPE/g" "$LAUNCHCONFIG".json
        exit_if_error $? "Unable to edit volume size in 'Launch configuration'"
    else
        sed -i -e "s/instance_type/$INSTANCETYPE/g" "$LAUNCHCONFIG".jsonma
        exit_if_error $? "Unable to edit volume size in 'Launch configuration'"
    fi

    log "Naming 'Launch configuration' to name inside the file"
    cat "$LAUNCHCONFIG".json | jq '(.LaunchConfigurationName += "_new")' > "$LAUNCHCONFIG"_new.json
    exit_if_error $? "Unable to name 'Launch configuration' file accurately"

    log "Creating duplicate of launch config and attaching to ASG"
    aws --profile "$PROFILE" --region "$REGION" autoscaling create-launch-configuration --cli-input-json file://"$LAUNCHCONFIG"_new.json --user-data file://"$LAUNCHCONFIG"_userdata.txt
    exit_if_error $? "Unable to create duplicate 'Launch configuration'"

    log "Updating ASG with new temp launch config"
    aws --profile "$PROFILE" --region "$REGION" autoscaling update-auto-scaling-group --auto-scaling-group-name "$ASGGROUP" --launch-configuration-name "$LAUNCHCONFIG"_new
    exit_if_error $? "Unable to update ASG with new temp 'Launch configuration'"

    log "Deleting existing launch config"
    aws --profile "$PROFILE" --region "$REGION" autoscaling  delete-launch-configuration --launch-configuration-name "$LAUNCHCONFIG"
    exit_if_error $? "Unable to delete existing 'Launch configuration'"

    log "Loading Launch config back with old name"
    aws --profile "$PROFILE" --region "$REGION" autoscaling create-launch-configuration --cli-input-json file://"$LAUNCHCONFIG".json --user-data file://"$LAUNCHCONFIG"_userdata.txt
    exit_if_error $? "Unable to load 'Launch configuration' back with old name"

    log "Updating ASG Group with new launch"
    aws --profile "$PROFILE" --region "$REGION" autoscaling update-auto-scaling-group --auto-scaling-group-name "$ASGGROUP" --launch-configuration-name "$LAUNCHCONFIG"
    exit_if_error $? "Unable to updae ASG with new 'Launch configuration'"

    log "Deleting uploaded launch config"
    aws --profile "$PROFILE" --region "$REGION" autoscaling  delete-launch-configuration --launch-configuration-name "$LAUNCHCONFIG"_new
    exit_if_error $? "Unable to delete existing 'Launch configuration'"

    log "Removing ASG Suspensions"
    aws --profile "$PROFILE" --region "$REGION" autoscaling resume-processes --auto-scaling-group-name "$ASGGROUP" --scaling-processes "Launch" "Terminate"

    log "Removing the json files"
    rm -rf "$LAUNCHCONFIG"_new.json "$LAUNCHCONFIG".json "$LAUNCHCONFIG".json
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
    elif [[ "$#" == 6 ]]; then
        PROFILE=$1
        REGION=$2
        ASGGROUP=$3
        LAUNCHCONFIG=$4
        INSTANCETYPE=$5
        AMIID=$6
        log "Profile: $PROFILE"
        log "Region: $REGION"
        log "Autoscaling Group Name: $ASGGROUP"
        log "Launch Configuration Name: $LAUNCHCONFIG"
        log "New Instance Type: $INSTANCETYPE"
        log "New AMI ID: $AMIID"
    else
        echo "All parameters not provided, please use command as below"
        echo "$0  AwsProfile Region AutoscalingGroup LaunchConfigurationName InstanceType AmiID(Optional)"
        exit 1
    fi
}

main()
{
    validate_parameters "$@"
    create_new_launch_config
}

main "$@"