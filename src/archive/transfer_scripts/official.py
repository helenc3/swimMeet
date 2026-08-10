from common.mongodb.connect import connect_to_mongodb
from common.mongodb.queries1 import findallbesttimes, get_seasons_and_teams
from common.utils import COLLECTION_NAME, OFFICIAL_COLLECTION_NAME


"""
migration script 
merge and move all docs in old collection "COLLECTION_NAME" to new collection "OFFICIAL_COLLECTION_NAME" in MongoDB
not part of main pipeline, useful for new data. 
"""

client, db = connect_to_mongodb()
official_collection = db[OFFICIAL_COLLECTION_NAME]
swimmers_collection = db[COLLECTION_NAME]

# Get swimmers who have 2025-2026 nj.com documents with non-empty data
swimmers = swimmers_collection.distinct(
    "swimmer",
    {
        "source": "njcom",
        "year": "2025-2026",
        "data": {"$exists": True, "$ne": [], "$not": {"$size": 0}}
    }
)

# get all the data for the swimmers
for swimmer in swimmers:
    seasons_teams = get_seasons_and_teams(swimmers_collection, swimmer)
    if "2025-2026" not in seasons_teams:
        continue
        
    best_times = findallbesttimes(swimmers_collection, swimmer)
    official_collection.update_one(
        {"swimmer": swimmer}, 
        {"$set": {"teams": seasons_teams,"best_times": best_times}},
        upsert=True
    )

    print(f"added {swimmer} to official collection")