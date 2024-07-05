import json

'''
Checks nuxeo data (a json file) for complex object component records
that are children of the same parent record and have duplicate
`pos` values. Creates an output file containing these duplicates.

Query that was run in psql to generate the json file that this 
script works with:

SELECT json_agg(h)
FROM (SELECT id, parentid, pos, name, isproperty, primarytype, istrashed FROM hierarchy
WHERE primarytype in ('SampleCustomPicture', 'CustomFile', 'CustomVideo', 'CustomAudio')
AND (istrashed IS NULL OR istrashed = 'f')
AND pos IS NOT NULL
AND parentid IS NOT NULL
ORDER BY parentid, pos) h;
'''
database_output = './output/nuxeo_db_complex_components_with_pos.json'

with open(database_output, "r") as f:
    components = f.read()

components = json.loads(components)

counts = {}
for c in components:
    unique_id = f"{c['parentid']}--{c['pos']}"
    if counts.get(unique_id):
        counts[unique_id] += 1
    else:
        counts[unique_id] = 1

duplicates = []
for id in counts:
    if counts[id] != 1:
        duplicates.append({"id": id, "count": counts[id]})

with open("./output/components_duplicate_pos.json", "w") as f:
    f.write(json.dumps(duplicates))
print(f"Wrote ./output/components_duplicate_pos.json")

#parent_ids = [d['id'].split('--')[0] for d in duplicates]
#print(set(parent_ids))
    


