#!/usr/bin/env python3
import csv
import sys
import json
import secretstorage

bus = secretstorage.dbus_init()
collection = secretstorage.get_default_collection(bus)

for item in collection.search_items({'source': 'keepass'}):
    item.delete()

if len(sys.argv) > 1:
    with open(sys.argv[1]) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for row in reader:
            print(row)
            secret = {
                'username': row[2],
                'password': row[3],
                'notes': row[5]
            }
            collection.create_item(row[1], {'url': row[4], 'source': 'keepass',
                                            'title': row[1]},
                                   json.dumps(secret))
