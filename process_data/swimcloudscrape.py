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

driver = webdriver.Chrome()
for swimmer in swimmers_to_lookup:
    swimmer_data = searchprofile(driver, swimmer)
    for profile in swimmer_data:
        profile_data = profile["data"]
        profile_name = profile["profile"]
        save_swimmer_to_mongodb(db, {'swimmer': swimmer, 'data': profile_data}, profile=profile_name, source='swimcloud')

driver.quit()














