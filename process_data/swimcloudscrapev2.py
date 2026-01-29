from sconeswimmer import parse_time_to_seconds, HSEVENTS, EQUIVALENT_EVENTS, ishsevent, splitevent, searchprofilev2
from mongodb_helper import connect_to_mongodb
from createswimmerprofsutils import convert_time_to_scy, OFFICIAL_COLLECTION_NAME
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
            print(f"  Profile {profile_idx + 1}: Empty, skipping")
            continue
        
        print(f"  Processing profile {profile_idx + 1}: {len(profile_data)} time entries")
        
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
                print(f"    Added: {target_event} = {time_scy:.2f}s (from {event} {course} {time_str})")
            else:
                print(f"    Skipped: {event} {course} (not mapped to HSEVENTS)")
    
    # Find best time for each event from newdata
    new_best_times = {}
    for event in HSEVENTS:
        if event in all_times_by_event and all_times_by_event[event]:
            new_best_times[event] = min(all_times_by_event[event])
    
    print(f"\nBest times from newdata: {new_best_times}")
    
    # Merge with old_best_times, keeping the faster time for each event
    updated_best_times = old_best_times.copy()
    
    print(f"\nComparing with old best times:")
    for event, new_time in new_best_times.items():
        current_time = old_best_times.get(event)
        
        # Update if: no current time (None) OR new time is faster
        if current_time is None:
            print(f"  {event}: None -> {new_time:.2f}s (NEW)")
            updated_best_times[event] = new_time
        elif new_time < current_time:
            print(f"  {event}: {current_time:.2f}s -> {new_time:.2f}s (FASTER)")
            updated_best_times[event] = new_time
        else:
            print(f"  {event}: {current_time:.2f}s (keeping, new {new_time:.2f}s is slower)")
    
    return updated_best_times

if __name__ == "__main__":
    client, db = connect_to_mongodb()
    if db is None:
        print("Failed to connect to MongoDB. Exiting.")
        exit(1)
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.page_load_strategy = "eager"
    driver = webdriver.Chrome(options=chrome_options)

    collection = db[OFFICIAL_COLLECTION_NAME]

    swimmer = "Adithi Srinivasan"
    urls = collection.find_one({"swimmer": swimmer})["swimcloud"]
    old_best_times = collection.find_one({"swimmer": swimmer})["best_times"]
    newdata = searchprofilev2(driver, urls, swimmer)
    print(newdata)
    updated_best_times = update_best_times(newdata, old_best_times)
    print(old_best_times)
    print("--------------------------------")
    print(updated_best_times)