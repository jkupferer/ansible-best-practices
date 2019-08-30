#!/usr/bin/env python
#
# A simple and fast dynamic inventory for AWS ec2
#
# Requires that instances are tagged with:
#
#   AnsibleInventory - Primary tag filter for selecting hosts
#
#   AnsibleGroups - Comma separated list of Ansible group names
#

import boto3
import json
import os
import sys

USAGE = """
Usage: hosts.py --list
   Or: hosts.py --host <hostname>
""".strip()

ec2 = None

def die(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)

def host_vars(name):
    return {}

def get_all_hosts():
    hostvars = {}
    ret = { '_meta': { 'hostvars': hostvars } }
    for response in ec2.get_paginator('describe_instances').paginate(
        Filters=[{
            'Name': 'tag:AnsibleInventory',
            'Values': [os.environ.get('ANSIBLE_INVENTORY', 'default')]
        }]
    ):
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                ansible_groups = []
                inventory_hostname = instance['PrivateDnsName']
                ec2_tags = {}
                for tag in instance.get('Tags', []):
                    ec2_tags[tag['Key']] = tag['Value']
                    if tag['Key'] == 'AnsibleGroups':
                        ansible_groups = tag['Value'].split(',')
                    elif tag['Key'] == 'Name':
                        inventory_hostname = tag['Value']
                hostvars[inventory_hostname] = {
                    'ansible_host': instance['PrivateIpAddress'],
                    'ec2_image_id': instance['ImageId'],
                    'ec2_instance_id': instance['InstanceId'],
                    'ec2_instance_type': instance['InstanceType'],
                    'ec2_subnet_id': instance['SubnetId'],
                    'ec2_tags': ec2_tags
                }
                for group in ansible_groups:
                    if group in ret:
                        ret[group].append(inventory_hostname)
                    else:
                        ret[group] = [inventory_hostname]

    return ret

def main():
    global ec2
    aws_region = os.environ.get('AWS_REGION')
    if not aws_region:
        die("AWS_REGION is required")
    ec2 = boto3.client('ec2', region_name=aws_region)
    if len(sys.argv) == 2 \
    and sys.argv[1] == '--list':
        print(json.dumps(
            get_all_hosts(),
            sort_keys=True,
            indent=2
        ))
    elif len(sys.argv) == 3 \
    and sys.argv[1] == '--host':
        print(json.dumps(
            host_vars(sys.argv[2]),
            sort_keys=True,
            indent=2
        ))
    else:
        die(USAGE)

if __name__ == '__main__':
    main()
