#!/opt/anaconda3/envs/py312/bin/python
from re import I
from sconeswimmer import searchprofile
from mongodb_helper import connect_to_mongodb, save_swimmer_to_mongodb, COLLECTION_NAME
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
import json

DATA_PATH = 'data/swimcloud'
SEASON = '2025-2026'


client, db = connect_to_mongodb()
if db is None:
    print("Failed to connect to MongoDB. Exiting.")
    exit(1)

collection = db[COLLECTION_NAME]

# Get list of unique swimmer names for the season
# Option 1: Get unique swimmers (recommended)
swimmers_to_lookup = collection.distinct("swimmer", {"year": SEASON, "source": "njcom"})

# Optimized Chrome options for faster scraping
chrome_options = Options()

# Disable images - HUGE speed boost (you only extract text, not images)
prefs = {
    "profile.managed_default_content_settings.images": 2,  # Block images
}
chrome_options.add_experimental_option("prefs", prefs)

# Performance optimizations
#chrome_options.add_argument("--headless")  # Run without GUI - faster!
chrome_options.add_argument("--disable-images")  # Don't load images
chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
chrome_options.add_argument("--no-sandbox")  # Faster startup
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
chrome_options.add_argument("--disable-extensions")  # Disable extensions
chrome_options.add_argument("--disable-plugins")  # Disable plugins
chrome_options.add_argument("--disable-logging")  # Disable verbose logging
chrome_options.add_argument("--log-level=3")  # Only show errors (0=info, 3=errors only)
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Less overhead

# Page load strategy - don't wait for all resources to load
chrome_options.page_load_strategy = "eager"  # Loads when DOM is ready, not all resources

driver = webdriver.Chrome(options=chrome_options)
# Set implicit wait to reduce need for fixed sleeps
driver.implicitly_wait(5)  # Wait up to 5 seconds for elements to appear

for swimmer in swimmers_to_lookup:
    # Check if this swimmer already has a directory in data/swimcloud (skip if exists)
    ## PLEASE COMMENT THIS OUT AFTER THIS RUN
    swimmer_dir = f"{DATA_PATH}/{swimmer}"
    if os.path.exists(swimmer_dir) and os.path.isdir(swimmer_dir):
        # Check if directory has any files (not just empty directory)
        files = [f for f in os.listdir(swimmer_dir) if os.path.isfile(os.path.join(swimmer_dir, f))]
        if len(files) > 0:
            print(f"⏭ Skipping {swimmer} - directory already exists with {len(files)} file(s) in {swimmer_dir}")
            continue
    
    swimmer_data = searchprofile(driver, swimmer)
    if swimmer_data is None:
        continue
    os.makedirs(f"{DATA_PATH}/{swimmer}", exist_ok=True)
    for profile in swimmer_data:
        profile_data = profile["data"]
        profile_name = profile["profile"]
        if profile_data is None:
            continue
        save_swimmer_to_mongodb(db, {'swimmer': swimmer, 'data': profile_data}, profile=profile_name, source='swimcloud')
        with open(f"{DATA_PATH}/{swimmer}/{profile_name}.json", "w", encoding="utf-8") as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
        print(f"Saved swimcloud data for {swimmer} {profile_name}")

driver.quit()














