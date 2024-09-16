import sys
import json
import requests

import psycopg2

import settings

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
        'url': u'/'.join([settings.NUXEO_API_ENDPOINT, "search/lang/NXQL/execute"]),
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

    print(f"{type(complex_obj_no_pos)=}")
    print(f"{len(complex_obj_no_pos)=}")
    print(f"{complex_obj_no_pos[0:10]=}")

    parents = {}

    # for obj in complex_obj_no_pos:
    #     parentid = obj['parentid']
    #     if parents.get(parentid):
    #         parents.get(parentid)['child_count'] += 1
    #     else:
    #         parents[parentid] = {"child_count": 1}

    # # we only want a list of parents with more than one child
    # for id in list(parents.keys()):
    #     child_count = parents[id]['child_count']
    #     if child_count <= 1:
    #         del parents[id]

    # print(f"Querying nuxeo for metadata for {len(parents)} objects")
    # for id in parents:
    #     nuxeo_data = get_nuxeo_data(id)
    #     for entry in nuxeo_data['entries']:
    #         parents[id]['path'] = entry['path']
    #         parents[id]['title'] = entry['title']
    #         parents[id]['type'] = entry['type']

    # # write json file containing parent objects whose children have no `pos`
    # with open("./output/complex_obj_null_pos.json", "w") as f:
    #     f.write(json.dumps(parents))
    # print(f"Wrote ./output/complex_obj_null_pos.json")

    # # write txt file containing parent object paths only
    # paths = [parents[id]['path'] for id in parents]
    # paths.sort()
    # with open("./output/complex_obj_null_pos_paths.txt", "a") as f:
    #     for path in paths:
    #         f.write(f"{path}\n")
    # print(f"Wrote ./output/complex_obj_null_pos_paths.txt")

if __name__ == '__main__':
     main()
     sys.exit(0)