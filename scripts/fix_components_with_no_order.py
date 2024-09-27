from collections import namedtuple
from datetime import datetime
import json
import requests
import sys
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor

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

def get_null_pos_complex_objects(cursor):
    '''
    Get list of complex object parent ids where at least one child has a hierarchy.pos of NULL
    '''
    query = """SELECT parentid
    FROM hierarchy
    WHERE parentid in (
        SELECT id FROM hierarchy
        WHERE primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio', 'CustomThreeD')
        AND (istrashed IS NULL OR istrashed = 'f')
    )
    AND primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio', 'CustomThreeD')
    AND (istrashed IS NULL OR istrashed = 'f')
    AND pos IS NULL"""

    cursor.execute(query)
    results = cursor.fetchall()
    ids = [result['parentid'] for result in results]
    return list(set(ids))

def get_children(parent_id, cursor):
    '''
    Get list of child objects ordered by name

    Returns a list of dicts, e.g.:

    [
        {'id': '1', 'parentid': '999', 'name': 'page1.tif'},
        {'id': '2', 'parentid': '999', 'name': 'page2.tif'}
    ]
    '''

    query = (
        "SELECT id, parentid, name "
        "FROM hierarchy "
        "WHERE primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio', 'CustomThreeD') "
        f"AND parentid = '{parent_id}' "
        "AND (istrashed IS NULL OR istrashed = 'f') "
        "ORDER BY name"
    )
    cursor.execute(query)
    results = cursor.fetchall()
    return results

def update_pos_in_db(id, pos, cursor):
    '''
    Assign hierarchy.pos value
    '''

    sql_update = (
        "UPDATE hierarchy "
        f"SET pos = {pos} "
        f"WHERE id = '{id}'"
    )

    cursor.execute(sql_update)

def reindex_doc_in_elasticsearch(id):
    '''
    Reindex document and its children in ElasticSearch
    '''
    url = f"{settings.NUXEO_API_ENDPOINT}/management/elasticsearch/{id}/reindex"
    request = {
        'url': url,
        'auth': (settings.NUXEO_API_USER, settings.NUXEO_API_PASS)
    }
    response = requests.post(**request)
    response.raise_for_status()

def main():
    '''
    Fix children of complex objects where at least one of the child docs has a NULL `hierarchy.pos`.
    Update the `hierarchy.pos` field for each child in the database, then reindex the document
    and its children in ElasticSearch.
    '''
    conn = psycopg2.connect(
        database=settings.NUXEO_DB_NAME,
        host=settings.NUXEO_DB_HOST,
        user=settings.NUXEO_DB_USER,
        password=settings.NUXEO_DB_PASS,
        port="5432")

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    #parents = get_null_pos_complex_objects(cursor)
    parents = parents[0:5] # FIXME
    database_updates = []
    for parent_id in parents:
        print(f"\nParent ID: {parent_id}")
        children = get_children(parent_id, cursor)
        print(f"Num of children: {len(children)}")
        pos = 0
        for child in children:
            print(f"Updating {child['name']} with pos {pos}")
            update_pos_in_db(child['id'], pos, cursor)
            pos += 1
            database_updates.append({
                "component_id": child['id'],
                "component_name": child['name'],
                "parent_id": parent_id,
                "pos": pos
            })
        conn.commit()

        print("Reindexing document and children")
        reindex_doc_in_elasticsearch(parent_id)

    version = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%dT%H:%M:%S.%Z')
    storage = parse_data_uri(settings.OUTPUT_URI)
    path = storage.path
    path = path.lstrip('/')

    s3_key = f"{path}/null_order_fix_report_{version}.json"
    load_object_to_s3(storage.bucket, s3_key, json.dumps(database_updates))

    print(
        f"\nUpdated {len(database_updates)} children of {len(parents)} objects\n"
        f"Database host: {settings.NUXEO_DB_HOST}\n"
        f"Nuxeo API endpoint: {settings.NUXEO_API_ENDPOINT}\n"
    )


if __name__ == '__main__':
    main()
    sys.exit(0)