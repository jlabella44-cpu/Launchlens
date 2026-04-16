#!/bin/bash
# Create the local S3 bucket for development
awslocal s3 mb s3://listingjet-media-local --region us-east-1
echo "LocalStack: created s3://listingjet-media-local"
