import argparse
import sys

import requests

import settings

nuxeo_request_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-NXDocumentProperties": "*",
        "X-NXRepository": "default",
        "X-Authentication-Token": settings.NUXEO
    }

def run_query(where_clause, endpoint):
    query = ("Select * from document "
            f"{where_clause} "
            "AND ecm:isVersion = 0 "
            "AND ecm:mixinType != 'HiddenInNavigation' "
            "AND ecm:isTrashed = 0 "
            "ORDER BY ecm:pos ASC"
    )
    request = {
        'url': endpoint,
        'headers': nuxeo_request_headers,
        'params': {
            'query': query
        }
    }
    response = requests.get(**request)
    response.raise_for_status()

    print(f"\n## endpoint: `{endpoint}`")
    print(f"## where clause: `{where_clause}`")
    entries = response.json()['entries']
    for e in entries:
        print(f"{e['uid']}, {e['title']}")


def get_path(id, endpoint):
    query = (
        "SELECT * FROM document "
        f"WHERE ecm:uuid = '{id}'"
    )
    request = {
        'url': endpoint,
        'headers': nuxeo_request_headers,
        'params': {
            'query': query
        }
    }
    response = requests.get(**request)
    response.raise_for_status()
    response = response.json()
    return response['entries'][0]['path']

def main(parent_id):
    '''
    Query Nuxeo for complex object components. Order results by `ecm:pos`
    
    Compare the ordering when using various combinations of Nuxeo API 
    endpoints and query clauses. The ordering is inconsistent when
    `hierarchy.pos` is null in the database, or more than one component
    has the same `hierarchy.pos` value.
    '''
    elasticsearch_endpoint = "https://nuxeo.cdlib.org/Nuxeo/site/api/v1/search/lang/NXQL/execute"
    database_endpoint = "https://nuxeo.cdlib.org/Nuxeo/site/api/v1/path/@search"

    parent_path = get_path(parent_id, elasticsearch_endpoint)

    id_where_clause = f"WHERE ecm:parentId =  '{parent_id}' "
    path_where_clause = f"WHERE ecm:path startswith '{parent_path}' "

    run_query(id_where_clause, database_endpoint)
    run_query(id_where_clause, elasticsearch_endpoint)
    run_query(path_where_clause, database_endpoint)
    run_query(path_where_clause, elasticsearch_endpoint)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("uid", help="UID of nuxeo complex object")
    args = parser.parse_args()
    main(args.uid)
    sys.exit(0)
