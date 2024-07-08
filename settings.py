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
NUXEO = os.environ.get("NUXEO_API_TOKEN")

DB_NAME = os.environ.get("NUXEO_DB_NAME")
DB_HOST = os.environ.get("NUXEO_DB_HOST")
DB_USER = os.environ.get("NUXEO_DB_USER")
DB_PASS = os.environ.get("NUXEO_DB_PASS")