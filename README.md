# Cloud Computing Project - Booklogr Web Application

## Booklogr

[GitHub](https://github.com/Mozzo1000/booklogr) 

## Description

This repository contains files needed to deploy the Booklogr application in AWS, using the AWS Academy Lab environment:
- `./templates` - CloudFormation templates for deploying the application infrastructure on AWS
- `./booklogr-web` - Copy of the SPA code for the Booklogr application, which should be deployed on anS3 bucket created by the CloudFormation templates
- `./load-testing` - various scripts for load testing using `locust`, and results of my runs of the tests

The backend is deployed using the official Booklogr Docker image, and therefore this repository does not contain the backend code. The backend code can be found in the [Booklogr repository](https://github.com/Mozzo1000/booklogr).

## Deployment instructions

- Deploy the infrastructure using the CloudFormation templates, following the instructions in the `cloudformation/README.md` file
- Create .env file for building the SPA: `cp booklogr-web/.env.example booklogr-web/.env`
- Update the .env file with the proper URL for the Load Balancer created by the CloudFormation templates
- Build the SPA: `npm install && npm run build`
- Upload the contents of the `booklogr-web/dist` folder to the S3 bucket created by the CloudFormation templates

The application should now be accessible through the URL of the S3 website hosting, which can be found in the CloudFormation stack outputs.
