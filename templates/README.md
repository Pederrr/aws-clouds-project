# CloudFormation templates

This directory contains CloudFormation templates for deploying the infrastructure.

## Usage

- The templates should be deployed in the order given by the number prefix in the filename (e.g. 1_x before 2_y).
- Each template exports outputs that are used as parameters for the next template in the sequence.
- Set the `LabRole` as IAM role
- For `5_auto_scaling_group.yaml`, you first need to create a AMI with pre-installed docker, and pulled the required docker images. Then set the `ImageId` parameter to the AMI ID of the created AMI. TO create the AMI, you can create a temporary EC2 instance with the Amazon Linux 2023 AMI, and the following user data, and then create an image after the instance is running:
```
#!/bin/bash
yum install docker -y
systemctl enable docker
systemctl start docker
docker pull mozzo/booklogr:v1.10.0
```
