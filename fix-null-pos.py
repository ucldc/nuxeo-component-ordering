import sys

import psycopg2
from psycopg2.extras import RealDictCursor

import settings

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

def update_pos(id, pos, cursor):
    '''
    Assign hierarchy.pos value
    '''

    sql_update = (
        "UPDATE hierarchy "
        f"SET pos = {pos} "
        f"WHERE id = '{id}'"
    )

    cursor.execute(sql_update)

def main():
    conn = psycopg2.connect(
        database=settings.DB_NAME,
        host=settings.DB_HOST,
        user=settings.DB_USER,
        password=settings.DB_PASS,
        port="5432")

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    parents = get_null_pos_complex_objects(cursor)
    #parents = parents[0:10]
    child_update_count = 0
    for parent_id in parents:
        print(f"\nParent ID: {parent_id}")
        children = get_children(parent_id, cursor)
        print(f"Num of children: {len(children)}")
        pos = 0
        for child in children:
            print(f"Updating {child['name']} with pos {pos}")
            update_pos(child['id'], pos, cursor)
            pos += 1
            child_update_count +=1
        conn.commit()

    print(f"\nUpdated {child_update_count} children of {len(parents)} objects")


if __name__ == '__main__':
    main()
    sys.exit(0)