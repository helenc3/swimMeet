from scraper.swimcloud.scutils import ishsevent, searchprofilev2
from common.mongodb.connect import connect_to_mongodb
from common.utils import (
    parse_time_to_seconds,
    HSEVENTS,
    EQUIVALENT_EVENTS,
    OFFICIAL_COLLECTION_NAME,
    convert_time_to_scy
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

"""
script used to update the best times for a swimmer in the new collection "OFFICIAL_COLLECTION_NAME" in MongoDB
part of main pipeline, functions here all helper and called nowhere else. 
"""

def update_best_times(newdata, old_best_times):
    """
    Process newdata from searchprofilev2, convert all times to SCY seconds,
    and return updated best_times dict with faster times.
    
    Args:
        newdata: List of lists - each inner list contains dicts with "event", "course", "time"
                 from scrapeprofile (one list per profile)
        old_best_times: Dict of {event: time_in_seconds} - current best times (can be None for events)
    
    Returns:
        Updated best_times dict with faster times from newdata merged in
    """
    if old_best_times is None:
        old_best_times = {}
    
    # Collect all times from all profiles, converted to SCY
    all_times_by_event = {}  # {event: [list of SCY times in seconds]}
    
    # Process each profile's data
    for profile_idx, profile_data in enumerate(newdata):
        if not profile_data:  # Skip empty profiles
            continue
        
        
        # profile_data is a list of dicts: [{"event": "...", "course": "...", "time": "..."}, ...]
        for time_entry in profile_data:
            event = time_entry.get("event", "")
            course = time_entry.get("course", "SCY")  # Default to SCY if not specified
            time_str = time_entry.get("time", "")
            
            if not event or not time_str:
                continue
            
            # Parse time to seconds
            time_seconds = parse_time_to_seconds(time_str)
            if time_seconds is None:
                print(f"    Warning: Could not parse time '{time_str}' for event '{event}'")
                continue
            
            # Check if this is a HS event (event is already just race name like "50 Free")
            # ishsevent expects format "50 Free SCY", so construct it
            event_with_course = f"{event} {course}" if course else event
            if not ishsevent(event_with_course):
                continue
            
            # Convert to SCY
            time_scy = convert_time_to_scy(time_seconds, event, course)
            if time_scy is None:
                print(f"    Warning: Could not convert time {time_seconds}s for event '{event}' course '{course}'")
                continue
            
            # Map event to HSEVENTS event (handle equivalent events)
            # event is already just the race name (e.g., "50 Free"), no need to split
            target_event = None
            
            if event in HSEVENTS:
                target_event = event
            elif event in EQUIVALENT_EVENTS:
                equivalent = EQUIVALENT_EVENTS[event]
                if equivalent in HSEVENTS:
                    target_event = equivalent
            else:
                # Check if any HSEVENTS event is equivalent to this event
                for hs_event in HSEVENTS:
                    if hs_event in EQUIVALENT_EVENTS and EQUIVALENT_EVENTS[hs_event] == event:
                        target_event = hs_event
                        break
            
            # Only process HSEVENTS events
            if target_event:
                if target_event not in all_times_by_event:
                    all_times_by_event[target_event] = []
                all_times_by_event[target_event].append(time_scy)
    
    # Find best time for each event from newdata
    new_best_times = {}
    for event in HSEVENTS:
        if event in all_times_by_event and all_times_by_event[event]:
            new_best_times[event] = min(all_times_by_event[event])
    
    
    # Merge with old_best_times, keeping the faster time for each event
    updated_best_times = old_best_times.copy()
    
    for event, new_time in new_best_times.items():
        current_time = old_best_times.get(event)
        
        # Update if: no current time (None) OR new time is faster
        if current_time is None:
            updated_best_times[event] = new_time
        elif new_time < current_time:
            updated_best_times[event] = new_time
    
    return updated_best_times

def update_one_swimmer(swimmer, collection, driver):
    doc = collection.find_one({"swimmer": swimmer})
    if not doc:
        raise ValueError(f"Swimmer '{swimmer}' not found in collection")
    
    urls = doc.get("swimcloud")
    if not urls:
        raise ValueError(f"Swimmer '{swimmer}' has no swimcloud field or it's empty")
    
    old_best_times = doc.get("best_times")
    newdata = searchprofilev2(driver, urls, swimmer)
    updated_best_times = update_best_times(newdata, old_best_times)
    collection.update_one({"swimmer": swimmer}, {"$set": {"best_times": updated_best_times}})

if __name__ == "__main__":
    client, db = connect_to_mongodb()
    if db is None:
        print("Failed to connect to MongoDB. Exiting.")
        exit(1)
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.page_load_strategy = "eager"
    driver = webdriver.Chrome(options=chrome_options)

    collection = db[OFFICIAL_COLLECTION_NAME]

    # # Find all swimmers with the swimcloud field (exists, not null, and not empty array)
    swimmers = collection.distinct("swimmer", {
        "$and": [
            {"swimcloud": {"$exists": True}},
            {"swimcloud": {"$ne": None}},
            {"swimcloud": {"$ne": []}}
        ]
    })

    for swimmer in swimmers:
        try:
            update_one_swimmer(swimmer, collection, driver)
            print(f"Updated {swimmer}")
        except Exception as e:
            print(f"Error updating {swimmer}: {e}")

    driver.quit()