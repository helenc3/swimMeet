from sconeswimmer import searchprofile
from mongodb_helper import connect_to_mongodb, save_swimmer_to_mongodb, COLLECTION_NAME
from selenium import webdriver

DATA_PATH = ''
SEASON = '2025-2026'


client, db = connect_to_mongodb()
if db is None:
    print("Failed to connect to MongoDB. Exiting.")
    exit(1)

collection = db[COLLECTION_NAME]

# Get list of unique swimmer names for the season
# Option 1: Get unique swimmers (recommended)
swimmers_to_lookup = collection.distinct("swimmer", {"year": SEASON, "source": "njcom"})
print(swimmers_to_lookup)
print(len(swimmers_to_lookup))
#driver = webdriver.Chrome()













