"""
Script to find swimmers with no swimcloud documents in the swimmers collection
"""
## this is a one time script 

from mongodb_helper import connect_to_mongodb, COLLECTION_NAME
from createswimmerprofsutils import OFFICIAL_COLLECTION_NAME
from sconeswimmer import open_and_search
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

def find_swimmers_without_swimcloud(collection=None, season="2025-2026"):
    """
    Find all swimmers in the collection that have no swimcloud documents,
    but only for swimmers who have non-empty 2025-2026 season documents.
    
    Args:
        collection: MongoDB collection object. If None, will connect automatically.
        season: Season year to check (default: "2025-2026")
    
    Returns:
        List of swimmer names (strings) that have no swimcloud documents
    """
    if collection is None:
        client, db = connect_to_mongodb()
        collection = db[COLLECTION_NAME]
    
    # Get swimmers who have non-empty 2025-2026 nj.com documents
    swimmers_with_season_data = collection.distinct(
        "swimmer",
        {
            "source": "njcom",
            "year": season,
            "data": {"$exists": True, "$ne": [], "$not": {"$size": 0}}
        }
    )
    
    swimmers_without_swimcloud = []
    
    for swimmer in swimmers_with_season_data:
        # Check if this swimmer has any swimcloud documents
        swimcloud_docs = collection.find_one({
            "swimmer": swimmer,
            "source": "swimcloud"
        })
        
        if swimcloud_docs is None:
            swimmers_without_swimcloud.append(swimmer)
    
    return swimmers_without_swimcloud

def add_swimclouds(driver, oldcollection, newcollection, missing_swimclouds_file="missingswimclouds.json"):
    """
    Goes through all swimcloud docs in the old collection, uses open_and_search to get 
    the swimcloud page URL, and adds it to the official collection as a 'swimcloud' field.
    Also handles swimmers from missingswimclouds.json file.
    If a swimmer has multiple swimcloud docs, all URLs are added as a list.
    
    Args:
        driver: Selenium WebDriver instance
        oldcollection: MongoDB collection with swimcloud documents (swimmers collection)
        newcollection: MongoDB collection to update (officialswimmerprofiles collection)
        missing_swimclouds_file: Path to JSON file with missing swimcloud URLs (default: "missingswimclouds.json")
    """
    # Track all swimmers we're processing to avoid duplicates
    processed_swimmers = set()
    # Track swimmers with errors
    swimmers_with_errors = []
    
    # First, process swimmers from the old collection
    swimmers_to_add = oldcollection.distinct("swimmer", {"source": "swimcloud"})
    
    print(f"Processing {len(swimmers_to_add)} swimmers with swimcloud documents from old collection...\n")
    
    for swimmer in swimmers_to_add:
        # Get all swimcloud documents for this swimmer
        swimcloud_docs = list(oldcollection.find({
            "swimmer": swimmer,
            "source": "swimcloud"
        }))
        
        if not swimcloud_docs:
            continue
        
        print(f"Processing {swimmer} ({len(swimcloud_docs)} profile(s))...")
        
        swimcloud_urls = []
        
        profile_errors = []
        for doc in swimcloud_docs:
            profile = doc.get("profile")
            if not profile:
                error_msg = f"No profile field found"
                print(f"  Warning: {error_msg} for {swimmer}, skipping document")
                profile_errors.append(error_msg)
                continue
            
            try:
                # Use open_and_search to navigate to the profile page
                open_and_search(driver, profile, enter=True)
                # Wait for page to load
                sleep(2)
                
                # Get the current URL
                url = driver.current_url
                if url and url not in swimcloud_urls:
                    swimcloud_urls.append(url)
                    print(f"  Found URL: {url}")
            except Exception as e:
                error_msg = f"Error getting URL for profile '{profile}': {str(e)}"
                print(f"  {error_msg}")
                profile_errors.append(error_msg)
                continue
        
        if swimcloud_urls:
            # Update the official collection document
            # Always store as a list for consistency
            swimcloud_value = swimcloud_urls
            
            result = newcollection.update_one(
                {"swimmer": swimmer},
                {"$set": {"swimcloud": swimcloud_value}},
                upsert=False  # Don't create if doesn't exist
            )
            
            if result.matched_count > 0:
                print(f"  ✓ Updated {swimmer} with {len(swimcloud_urls)} swimcloud URL(s)")
            else:
                error_msg = f"Swimmer not found in official collection"
                print(f"  ⚠ Warning: {error_msg}")
                swimmers_with_errors.append({
                    "swimmer": swimmer,
                    "error": error_msg,
                    "profiles_attempted": len(swimcloud_docs),
                    "urls_found": len(swimcloud_urls)
                })
        else:
            error_msg = f"No URLs found for any profiles"
            print(f"  ⚠ {error_msg}")
            swimmers_with_errors.append({
                "swimmer": swimmer,
                "error": error_msg,
                "profile_errors": profile_errors,
                "profiles_attempted": len(swimcloud_docs)
            })
        
        if swimcloud_urls:
            processed_swimmers.add(swimmer)
        
        print()  # Empty line for readability
    
    # Now process swimmers from missingswimclouds.json
    try:
        with open(missing_swimclouds_file, 'r', encoding='utf-8') as f:
            missing_swimclouds = json.load(f)
        
        print("="*60)
        print(f"Processing {len(missing_swimclouds)} swimmers from {missing_swimclouds_file}...\n")
        
        for swimmer, url in missing_swimclouds.items():
            if not url:
                print(f"  ⚠ Warning: No URL provided for {swimmer}, skipping")
                continue
            
            print(f"Processing {swimmer} from missing swimclouds file...")
            
            # Check if swimmer already has URLs from old collection
            existing_doc = newcollection.find_one({"swimmer": swimmer})
            existing_urls = []
            
            if existing_doc and "swimcloud" in existing_doc:
                existing_swimcloud = existing_doc["swimcloud"]
                if isinstance(existing_swimcloud, list):
                    existing_urls = existing_swimcloud
                elif isinstance(existing_swimcloud, str):
                    existing_urls = [existing_swimcloud]
            
            # Add the URL from the file if not already present
            all_urls = existing_urls.copy()
            if url not in all_urls:
                all_urls.append(url)
                print(f"  Added URL: {url}")
            else:
                print(f"  URL already exists: {url}")
            
            # Update the official collection document
            result = newcollection.update_one(
                {"swimmer": swimmer},
                {"$set": {"swimcloud": all_urls}},
                upsert=False  # Don't create if doesn't exist
            )
            
            if result.matched_count > 0:
                print(f"  ✓ Updated {swimmer} with {len(all_urls)} swimcloud URL(s)")
            else:
                error_msg = f"Swimmer not found in official collection"
                print(f"  ⚠ Warning: {error_msg}")
                swimmers_with_errors.append({
                    "swimmer": swimmer,
                    "error": error_msg,
                    "source": "missingswimclouds.json",
                    "url": url
                })
            
            print()  # Empty line for readability
            
    except FileNotFoundError:
        print(f"  ⚠ Warning: {missing_swimclouds_file} not found, skipping missing swimclouds processing")
    except json.JSONDecodeError as e:
        print(f"  ⚠ Error reading {missing_swimclouds_file}: {e}")
    except Exception as e:
        print(f"  ⚠ Error processing missing swimclouds: {e}")
    
    print("="*60)
    print("Completed processing swimcloud URLs")
    print("="*60)
    
    # Write swimmers with errors to a file
    if swimmers_with_errors:
        error_file = "swimcloud_errors.json"
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(swimmers_with_errors, f, indent=2, ensure_ascii=False)
        print(f"\n⚠ {len(swimmers_with_errors)} swimmer(s) had errors - saved to {error_file}")
    else:
        print("\n✓ No errors encountered!")


if __name__ == "__main__":
    client, db = connect_to_mongodb()
    old_collection = db[COLLECTION_NAME]
    new_collection = db[OFFICIAL_COLLECTION_NAME]
    chrome_options = Options()
    
    # Disable images - HUGE speed boost
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Block images
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Performance optimizations (similar to other working scripts)
    chrome_options.add_argument("--disable-images")  # Don't load images
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    # Note: --no-sandbox can cause issues on macOS, try without it first
    # chrome_options.add_argument("--no-sandbox")  # Faster startup (may cause issues on macOS)
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-plugins")  # Disable plugins
    chrome_options.add_argument("--disable-logging")  # Disable verbose logging
    chrome_options.add_argument("--log-level=3")  # Only show errors
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Less overhead
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.page_load_strategy = "eager"  # Loads when DOM is ready, not all resources
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        # Set implicit wait to reduce need for fixed sleeps
        driver.implicitly_wait(5)
        add_swimclouds(driver, old_collection, new_collection)
        driver.quit()
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Chrome and ChromeDriver versions match")
        print("2. Try closing any existing Chrome instances")
        print("3. Check if ChromeDriver is in your PATH")
        print("4. On macOS, you may need to allow ChromeDriver in System Preferences > Security")
        raise

