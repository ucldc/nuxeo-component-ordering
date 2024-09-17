import os

from boto3 import Session
from opensearchpy import AWSV4SignerAuth

def get_aws_auth():
    credentials = Session().get_credentials()
    if not credentials:
        return False
    return AWSV4SignerAuth(
        credentials, os.environ.get("AWS_REGION", "us-west-2"))

OUTPUT_URI = os.environ.get("OUTPUT_URI")

OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT")

NUXEO_API_ENDPOINT = os.environ.get("NUXEO_API_ENDPOINT")
NUXEO_API_TOKEN = os.environ.get("NUXEO_API_TOKEN")
NUXEO_API_USER = os.environ.get("NUXEO_API_USER")
NUXEO_API_PASS = os.environ.get("NUXEO_API_PASS")

NUXEO_DB_NAME = os.environ.get("NUXEO_DB_NAME")
NUXEO_DB_HOST = os.environ.get("NUXEO_DB_HOST")
NUXEO_DB_USER = os.environ.get("NUXEO_DB_USER")
NUXEO_DB_PASS = os.environ.get("NUXEO_DB_PASS")