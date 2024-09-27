from collections import namedtuple
from datetime import datetime
import sys
import json
import requests
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import boto3
import psycopg2

import settings

# TODO: if we ever have to run these scripts again, put storage utils in a shared file
DataStorage = namedtuple(
    "DateStorage", "uri, store, bucket, path"
)

def parse_data_uri(data_uri: str):
    data_loc = urlparse(data_uri)
    return DataStorage(
        data_uri, data_loc.scheme, data_loc.netloc, data_loc.path)


def load_object_to_s3(bucket, key, content):
    s3_client = boto3.client('s3')
    print(f"Writing s3://{bucket}/{key}")
    try:
        s3_client.put_object(
            ACL='bucket-owner-full-control',
            Bucket=bucket,
            Key=key,
            Body=content)
    except Exception as e:
        print(f"ERROR loading to S3: {e}")

    return f"s3://{bucket}/{key}"

def get_complex_obj_no_pos():
    '''
    Find all complex object components (children) where pos is null.

    Returns a list of results in json format.
    '''
    conn = psycopg2.connect(database=settings.NUXEO_DB_NAME,
                        host=settings.NUXEO_DB_HOST,
                        user=settings.NUXEO_DB_USER,
                        password=settings.NUXEO_DB_PASS,
                        port="5432")
    

    cursor = conn.cursor()
    query = (
        "SELECT json_agg(h) "
        "FROM (SELECT id, parentid, pos, name, isproperty, primarytype, istrashed "
        "FROM hierarchy "
        "WHERE parentid in ( "
        "   SELECT id FROM hierarchy "
        "   WHERE primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio', 'CustomThreeD') "
        "   AND (istrashed IS NULL OR istrashed = 'f') "
        ") "
        "AND primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio', 'CustomThreeD') "
        "AND (istrashed IS NULL OR istrashed = 'f') "
        "AND pos IS NULL) h;"
    )
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return results[0][0]


def get_nuxeo_data(id):
    # get full data for object using nuxeo API
    nuxeo_request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-NXDocumentProperties": "*",
            "X-NXRepository": "default",
        }

    query = (
                "SELECT * FROM Documents "
                f"WHERE ecm:uuid = '{id}' "
                "AND ecm:isVersion = 0 "
                "AND ecm:mixinType != 'HiddenInNavigation' "
                "AND ecm:isTrashed = 0 "
            )

    request = {
        'url': u'/'.join([settings.NUXEO_API_ENDPOINT, "search/lang/NXQL/execute"]),
        'headers': nuxeo_request_headers,
        'params': {
            'query': query
        },
        'auth': (settings.NUXEO_API_USER, settings.NUXEO_API_PASS)
    }

    try:
        resp = requests.get(**request)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"unable to fetch components from nuxeo: {request}")
        raise(e)

    nuxeo_data = resp.json()
    return nuxeo_data

def main():
    '''
    Create report listing complex objects in Nuxeo whose children have
    a `hierarchy.pos` field of NULL. Only includes objects with more
    than 1 child.
    '''
    complex_obj_no_pos = get_complex_obj_no_pos()
    if complex_obj_no_pos:
        parents = {}

        for obj in complex_obj_no_pos:
            parentid = obj['parentid']
            if parents.get(parentid):
                parents.get(parentid)['child_count'] += 1
            else:
                parents[parentid] = {"child_count": 1}

        # we only want a list of parents with more than one child
        for id in list(parents.keys()):
            child_count = parents[id]['child_count']
            if child_count <= 1:
                del parents[id]

        for id in parents:
            nuxeo_data = get_nuxeo_data(id)
            for entry in nuxeo_data['entries']:
                parents[id]['path'] = entry['path']
                parents[id]['title'] = entry['title']
                parents[id]['type'] = entry['type']

        version = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%dT%H:%M:%S.%Z')
        storage = parse_data_uri(settings.OUTPUT_URI)
        path = storage.path
        path = path.lstrip('/')

        # write json file
        s3_key = f"{path}/complex_obj_no_order_{version}.json"
        load_object_to_s3(storage.bucket, s3_key, json.dumps(parents))

        # write txt file containing parent object paths only
        s3_key = f"{path}/complex_obj_no_order_paths_{version}.txt"
        parent_paths = [parents[id]['path'] for id in parents]
        parent_paths.sort()
        parent_paths = "\n".join(parent_paths)
        load_object_to_s3(storage.bucket, s3_key, parent_paths)

        print(f"Found {len(complex_obj_no_pos)} total parent objects with ordering problem.\n"
              f"Found {len(parents)} problematic parent objects with > 1 component.\n"
              f"Database host: {settings.NUXEO_DB_HOST}\n"
        )
    else:
        print(
            "Found zero complex object components with null position.\n"
            f"Database host: {settings.NUXEO_DB_HOST}\n"
        )

if __name__ == '__main__':
     main()
     sys.exit(0)