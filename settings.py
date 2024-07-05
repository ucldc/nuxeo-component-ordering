import os

from boto3 import Session
from opensearchpy import AWSV4SignerAuth

def get_auth():
    credentials = Session().get_credentials()
    if not credentials:
        return False
    return AWSV4SignerAuth(
        credentials, os.environ.get("AWS_REGION", "us-west-2"))

OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT")
NUXEO = os.environ.get("NUXEO_TOKEN")