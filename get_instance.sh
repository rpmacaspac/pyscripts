#!/bin/bash

# Run the aws ec2 describe-instances command and output to JSON
instance_info=$(aws ec2 describe-instances --instance-ids i-0f203cb6f7fb5a8db --output json)

# Parse JSON and extract variables
instance_profile=$(echo $instance_info | jq -r '.Reservations[].Instances[].IamInstanceProfile.Arn')
ami_id=$(echo $instance_info | jq -r '.Reservations[].Instances[].ImageId')
key_pair=$(echo $instance_info | jq -r '.Reservations[].Instances[].KeyName'
subnet_id=$(echo $instance_info | jq -r '.Reservations[].Instances[].SubnetId')
security_groups=$(echo $instance_info | jq -r '.Reservations[].Instances[].SecurityGroups[].GroupId' | sed 's/.*/"&"/g' | tr "\n" " ")
instance_type=$(echo $instance_info | jq -r '.Reservations[].Instances[].InstanceType')

# Print the extracted variables
echo "Instance_Profile: $instance_profile"
echo "AMI_ID: $ami_id"
echo "Key_Pair: $key_pair"
echo "Subnet_ID: $subnet_id"
echo "Security_Groups: $security_groups"
echo "Instance_Type: $instance_type"

#--image-id $AMI_ID --security-group-ids $Security_Groups --iam-instance-profile $Instance_Profile --subnet-id $Subnet_ID --instance-type $Instance_Type --key-name $Key_Pair