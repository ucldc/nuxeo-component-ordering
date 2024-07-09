from datetime import datetime
import json
import sys

import requests

import settings

def get_opensearch_data(collection_id):
    '''
    Query rikolti opensearch stage index for complex objects
    that belong to a particular collection
    '''
    url = f"{settings.OPENSEARCH_ENDPOINT}/rikolti-stg/_search"
    data = {
        "query": {
            "bool": {
                "must": [
                    {
                        "nested": {
                            "path": "children",
                            "query": {
                                "match_all": {}
                            }
                        }
                    }
                ],
                "filter": [
                    {
                        "term": {
                            "collection_url": collection_id
                        }
                    }
                ]
            }
        },
        "size": 3000
    }
    headers = {"Content-Type": "application/json"}
    r = requests.get(
        url,
        headers=headers,
        data=json.dumps(data),
        auth=settings.get_aws_auth()
    )
    r.raise_for_status()

    opensearch_data = r.json()
    return opensearch_data

def get_nuxeo_data(parent_id):
    '''
    Query Nuxeo for child objects of a given parent
    '''
    headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-NXDocumentProperties": "*",
            "X-NXRepository": "default",
            "X-Authentication-Token": settings.NUXEO_TOKEN
        }

    query = (
                "SELECT * FROM SampleCustomPicture, CustomFile, "
                "CustomVideo, CustomAudio, CustomThreeD "
                f"WHERE ecm:parentId = '{parent_id}' "
                "AND ecm:isVersion = 0 "
                "AND ecm:mixinType != 'HiddenInNavigation' "
                "AND ecm:isTrashed = 0 "
                "ORDER BY ecm:pos ASC"
            )

    request = {
        'url': "https://nuxeo.cdlib.org/Nuxeo/site/api/v1/search/lang/NXQL/execute",
        'headers': headers,
        'params': {
            'pageSize': '1000',
            'currentPageIndex': 0,
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

def get_calisphere_collections_with_complex_objects():
    '''
    query the rikolti opensearch stage index for a list of collections with complex objects

    Returns a list of format:
    [
        {'key': '508', 'doc_count': 1},
        {'key': '5809', 'doc_count': 1},
        {'key': '85', 'doc_count': 1}
    ]

    Where 'key' in collection ID and 'doc_count' is number of documents.
    '''
    url = f"{settings.OPENSEARCH_ENDPOINT}/rikolti-stg/_search"
    data = {
        "query": {
            "nested": {
            "path": "children",
            "query": {
                "match_all": {}
            }
            }
        },
        "aggs": {
            "collection_ids": {
            "terms": {
                "field": "collection_url",
                "size": 10000
            }
            }
        },
        "size": 0
    }
    headers = {"Content-Type": "application/json"}
    r = requests.get(
        url,
        headers=headers,
        data=json.dumps(data),
        auth=settings.get_aws_auth(),
    )
    r.raise_for_status()
    response = r.json()
    return response['aggregations']['collection_ids']['buckets']
    
def main():
    '''
    Check component ordering in rikolti OpenSearch index 
    vs the order returned by the Nuxeo API. Output a report
    of objects where the order doesn't match.

    This script was written because contributors noticed
    that complex objects were not retaining their order
    when harvested through to Calisphere. This script tries
    to identify records in the rikolti index whose order
    is different from what's in Nuxeo.
    '''
    # get list of collections on calisphere-stage that have complex objects
    collections = get_calisphere_collections_with_complex_objects()

    collection_check_total = 0

    # loop through collections
    mismatches = []
    for collection in collections:

        # skip collections with over n complex objects (for dev purposes)
        if collection['doc_count'] > 1:
             continue
       
        collection_id = collection['key']
        
        opensearch_data = get_opensearch_data(collection_id)
        collection_check_total += 1

        print(f"checking {collection_id} ({len(opensearch_data['hits']['hits'])} complex objs)")
        
        # loop through opensearch parent objects
        for hit in opensearch_data['hits']['hits']:
            parent_id = hit['_source']['calisphere-id']
            
            # get list of opensearch child ids
            opensearch_children = hit['_source'].get('children')
            opensearch_ids = [child['calisphere-id'] for child in opensearch_children]
            
            # get list of nuxeo child ids
            nuxeo_data = get_nuxeo_data(parent_id)
            nuxeo_ids = [entry['uid'] for entry in nuxeo_data['entries']]

            # get info on any mismatches
            mismatch = {}
            if opensearch_ids != nuxeo_ids:
                opensearch_titles = [child['title'][0] for child in opensearch_children]
                nuxeo_titles = [entry['title'] for entry in nuxeo_data['entries']]
                mismatch = {
                    "collection_id": collection_id,
                    "parent_id": parent_id,
                    "title": hit['_source']['title'],
                    "nuxeo_ids": nuxeo_ids,
                    "opensearch_ids": opensearch_ids,
                    "nuxeo_titles": nuxeo_titles,
                    "opensearch_titles": opensearch_titles
                }
                mismatches.append(mismatch)

                # print some info
                count_diff = ''
                if len(opensearch_ids) != len(nuxeo_ids):
                    count_diff = f" - also count diff {len(opensearch_ids)} vs {len(nuxeo_ids)}"
                print(f"   mismatch for {parent_id}{count_diff}")

    date_string = datetime.now().strftime("%Y%m%d")
    output_file = f"./output/compare_child_order_rikolti_vs_nuxeo_{date_string}.json"
    with open(output_file, "w") as f:     
         f.write(json.dumps(mismatches))
    print(f"\nReport written to {output_file}")

    # print a count of objects per collection with the ordering problem
    with open(output_file, "r") as f:
        mismatches = json.loads(f.read())
    collections = [m['collection_id'] for m in mismatches]
    count_total = 0
    collection_counts = {}
    for id in collections:
        if collection_counts.get(id):
            collection_counts[id] = collection_counts[id] + 1
        else:
            collection_counts[id] = 1
        count_total += collection_counts[id]

    # print summary info
    print(f"Found {count_total} mismatches for {len(collections)} collections. Checked {collection_check_total} collections total.")
    print("\nCollection ID  Count of complex objs with ordering problem")
    for c in collection_counts:
        print(f"{c.ljust(14)} {collection_counts[c]}")

    


if __name__ == "__main__":
     main()
     sys.exit(0)