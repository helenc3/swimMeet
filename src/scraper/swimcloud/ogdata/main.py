#!/opt/anaconda3/envs/py312/bin/python
from scraper.swimcloud.scutils import searchprofile, save_swimmer_to_mongodb
from common.mongodb.connect import connect_to_mongodb
from common.utils import COLLECTION_NAME, SWIMCLOUD_DATA_DIR
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

"""
script used to scrape original swimcloud data for njcom swimmers
used to update the old collection "COLLECTION_NAME" in mongodb with new swimcloud times
saves backup copy in data directory
not part of main pipeline, useful for new data. 
"""

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
    swimmer_dir = SWIMCLOUD_DATA_DIR / swimmer
    if swimmer_dir.exists() and swimmer_dir.is_dir():
        # Check if directory has any files (not just empty directory)
        files = [f for f in swimmer_dir.iterdir() if f.is_file()]
        if len(files) > 0:
            print(f"⏭ Skipping {swimmer} - directory already exists with {len(files)} file(s) in {swimmer_dir}")
            continue
    
    swimmer_data = searchprofile(driver, swimmer)
    if swimmer_data is None:
        continue
    swimmer_dir.mkdir(parents=True, exist_ok=True)
    for profile in swimmer_data:
        profile_data = profile["data"]
        profile_name = profile["profile"]
        if profile_data is None:
            continue
        save_swimmer_to_mongodb(db, {'swimmer': swimmer, 'data': profile_data}, profile=profile_name, source='swimcloud')
        with open(swimmer_dir / f"{profile_name}.json", "w", encoding="utf-8") as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
        print(f"Saved swimcloud data for {swimmer} {profile_name}")

driver.quit()














