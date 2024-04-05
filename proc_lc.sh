#!/bin/bash

log_message() {
    echo "$(date +"%Y-%m-%d %T"): $1"
}

log_message "Script execution started."

if [ $# -eq 0 ]; then
    log_message "Usage: $0 <launch_configuration_names>"
    echo "Usage: $0 <launch_configuration_names>" >&2
    exit 1
fi

log_message "Generating an empty Launch Configuration JSON."
# Generate an empty Launch Configuration JSON and throw an error if failed
aws autoscaling create-launch-configuration --generate-cli-skeleton > "./lc_empty.json" || { log_message "Create launch configuration failed."; echo "Create launch configuration failed." >&2; exit 2; }

log_message "Describing Launch Configurations."
# Describe Launch Configurations and save to file
aws autoscaling describe-launch-configurations --launch-configuration-names "$1" --region ap-northeast-1 > "./lc_faulty.json" || { log_message "Describe launch configuration failed. Please check that the launch configuration exists."; echo "Describe launch configuration failed. Please check that the launch configuration exists." >&2; exit 3; }

# Decode UserData and save to file and throw an error if failed
log_message "Decoding UserData and saving to file."
cat "./lc_faulty.json" | jq -r '.LaunchConfigurations[].UserData' | base64 -d > "./user_data_decoded.txt" || { log_message "Creating decoded UserData failed."; echo "Creating decoded UserData failed." >&2; exit 4; }

# Create cluster name based on launch configuration name and current date and throw an error if failed
log_message "Creating launch configuration name."
lc_name=$(jq -r '.LaunchConfigurations[].LaunchConfigurationName' "./lc_faulty.json" | awk -F'-' '{NF--; OFS="-"; print}')-$(date +"%Y%m%d").json || { log_message "Cannot parse LC name. Check the fault json file."; echo "Cannot parse LC name. Check the fault json file." >&2; exit 5; }

# Manipulate JSON to remove UserData and filter BlockDeviceMappings, then save to file
log_message "Manipulating JSON and saving to file."
cat "./lc_faulty.json" | jq '.LaunchConfigurations[].BlockDeviceMappings |= map(select(.DeviceName == "/dev/xvdcz")) | del(.LaunchConfigurations[].UserData)' > "$lc_name" || { log_message "Cannot create the launch configuration json file."; echo "Cannot create the launch configuration json file" >&2; exit 5; }

sed -i 's/"LaunchConfigurationName": ".*"/"LaunchConfigurationName": "'"$lc_name"'"/' $lc_name
# Remove .json extension to get launch configuration name
lc_name="${lc_name%.json}"

# Read the faulty JSON
faulty_json=$(cat $lc_name.json)

# Extract parameters from faulty JSON
lc_name=$(echo "$faulty_json" | jq -r '.LaunchConfigurations[0].LaunchConfigurationName' | cut -d"." -f1)
image_id=$(echo "$faulty_json" | jq -r '.LaunchConfigurations[0].ImageId')
key_name=$(echo "$faulty_json" | jq -r '.LaunchConfigurations[0].KeyName')
security_groups=$(jq -r '.LaunchConfigurations[0].SecurityGroups | map("\"" + . + "\"") | join(",")' "./lc_faulty.json")instance_type=$(echo "$faulty_json" | jq -r '.LaunchConfigurations[0].InstanceType')
block_device_mappings=$(echo "$faulty_json" | jq -r '.LaunchConfigurations[0].BlockDeviceMappings | @json')
iam_instance_profile=$(echo "$faulty_json" | jq -r '.LaunchConfigurations[0].IamInstanceProfile')
instance_monitoring_enabled=$(echo "$faulty_json" | jq -r '.LaunchConfigurations[0].InstanceMonitoring.Enabled')

# Create the skeleton JSON with populated parameters
log_message "Creating the skeleton JSON with populated parameters."
skeleton_json='{
    "LaunchConfigurationName": "'${lc_name%.json}'",
    "ImageId": "'$image_id'",
    "KeyName": "'$key_name'",
    "SecurityGroups": ['$security_groups'],
    "InstanceType": "'$instance_type'",
    "BlockDeviceMappings": '$block_device_mappings',
    "IamInstanceProfile": "'$iam_instance_profile'",
    "InstanceMonitoring": {
        "Enabled": '$instance_monitoring_enabled'
    },
    "EbsOptimized": false
}'

# Print the populated JSON
echo "$skeleton_json" > new_input.json

log_message "Launch configuration name: ${lc_name%.json}"

# Prompt user to confirm
read -r -p "Do you want to continue and create a new launch configuration? (y/n): " choice
case "$choice" in
  y|Y )
    log_message "Creating a new launch configuration."
    # Final command to create a new launch configuration
    if aws autoscaling create-launch-configuration --cli-input-json file://new_input.json --user-data file://"./user_data_decoded.txt" --launch-configuration-name "$lc_name"; then
      log_message "Launch configuration created successfully."
    else
      log_message "Error: Failed to create launch configuration"
    fi
    ;;
  n|N )
    log_message "Operation cancelled."
    echo "Operation cancelled."
    ;;
  * )
    log_message "Invalid choice. Operation cancelled."
    echo "Invalid choice. Operation cancelled."
    ;;
esac