import sys
import json
import requests

import psycopg2

import settings

def get_complex_obj_no_pos():
    '''
    Find all complex object components (children) where pos is null.
    '''
    conn = psycopg2.connect(database=settings.NUXEO_DB_NAME,
                        host=settings.NUXEO_DB_HOST,
                        user=settings.NUXEO_DB_USER,
                        password=settings.NUXEO_DB_PASS,
                        port="5432")
    

    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM hierarchy")
    print(cursor.fetchone())
     
    '''
    Run the following query against the database on a machine in the nuxeo VPC:
    
    SELECT json_agg(h)
    FROM (SELECT id, parentid, pos, name, isproperty, primarytype, istrashed
        FROM hierarchy
        WHERE parentid in (
            SELECT id FROM hierarchy
            WHERE primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio', 'CustomThreeD')
            AND (istrashed IS NULL OR istrashed = 'f')
        )
        AND primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio', 'CustomThreeD')
        AND (istrashed IS NULL OR istrashed = 'f')
        AND pos IS NULL) h
        ;
    '''
    # with open("./output/nuxeo_db_complex_components_null_pos.json", "r") as f:
    #     complex_obj = f.read()

    # return json.loads(complex_obj)

def get_nuxeo_data(id):
    # get full data for object using nuxeo API
    nuxeo_request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-NXDocumentProperties": "*",
            "X-NXRepository": "default",
            "X-Authentication-Token": settings.NUXEO_API_TOKEN
        }

    query = (
                "SELECT * FROM Documents "
                f"WHERE ecm:uuid = '{id}' "
                "AND ecm:isVersion = 0 "
                "AND ecm:mixinType != 'HiddenInNavigation' "
                "AND ecm:isTrashed = 0 "
            )

    request = {
        'url': "https://nuxeo.cdlib.org/Nuxeo/site/api/v1/search/lang/NXQL/execute",
        'url': f"{settings.NUXEO_API_ENDPOINT}"
        'headers': nuxeo_request_headers,
        'params': {
            'query': query
        }
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


if __name__ == '__main__':
     main()
     sys.exit(0)