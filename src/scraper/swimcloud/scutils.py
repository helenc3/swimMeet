from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from datetime import datetime, date
from common.utils import (
    HSEVENTS,
    EQUIVALENT_EVENTS,
    COLLECTION_NAME,
    TIMEEXPIRATION,
    STATE,
    SWIMCLOUD_DATA_DIR,
    SWIMCLOUD_PROBLEMS_FILE,
    parse_time_to_seconds,
)

def ishsevent(event):
    ###### return True if the event is a HS event, False otherwise
    ##### input is a string in the format of "50 Free SCY"
    ##### checks HSEVENTS and also equivalent events (e.g., 400 Free matches 500 Free)
    race, course = splitevent(event)
    # Check if race is directly in HSEVENTS
    if race in HSEVENTS:
        return True
    # Check if race is equivalent to any event in HSEVENTS
    if race in EQUIVALENT_EVENTS:
        equivalent = EQUIVALENT_EVENTS[race]
        if equivalent in HSEVENTS:
            return True
    # Check if any event in HSEVENTS is equivalent to this race
    for hs_event in HSEVENTS:
        if hs_event in EQUIVALENT_EVENTS and EQUIVALENT_EVENTS[hs_event] == race:
            return True
    return False

def validdate(date_str): 
    """
    date_str is a string in the format of "Jan 23, 2025" or "Jan 3, 2025" (with or without leading zero)
    Returns True if the date is within TIMEEXPIRATION years to the last November 1st that occurred, False otherwise
    """
    try:
        date_str = date_str.strip()
        
        # try parsing with different formats
        # Format 1: "Jan 23, 2025" -> "%b %d, %Y" (with leading zero)
        # Format 2: "Jan 3, 2025" -> "%b %-d, %Y" (without leading zero) 
        # try both formats
        
        try:
            # try standard format first
            parsed_date = datetime.strptime(date_str, "%b %d, %Y").date()
        except ValueError:
            # try without leading zero - manually handle single digit days
            # replace "Jan 3, 2025" -> "Jan 03, 2025"
            import re
            # match pattern like "Jan 3, 2025" and pad to "Jan 03, 2025"
            date_str_padded = re.sub(r'(\w+) (\d{1}), (\d{4})', r'\1 0\2, \3', date_str)
            parsed_date = datetime.strptime(date_str_padded, "%b %d, %Y").date()
        
        # get current date
        today = date.today()
        
        # find the last November 1st that occurred
        # of we're in Nov or Dec, last Nov 1st is this year's Nov 1
        # otherwise, last Nov 1st is last year's Nov 1
        if today.month >= 11:  # November or December
            last_nov_1 = date(today.year, 11, 1)
        else:  # January through October
            last_nov_1 = date(today.year - 1, 11, 1)
        
        # Calculate Nov 1st of TIMEEXPIRATION years before the last Nov 1st
        nov_1_expiration_years_ago = date(last_nov_1.year - TIMEEXPIRATION, 11, 1)
        
        # Check if date is between Nov 1st (TIMEEXPIRATION years ago) and last Nov 1st
        return nov_1_expiration_years_ago <= parsed_date
        
    except (ValueError, AttributeError) as e:
        # If date parsing fails, print debug info and return False
        print(f"Warning: Could not parse date '{date_str}': {e}")
        return False


def select_event_from_dropdown(driver, event_name):
    """
    Selects an event from the dropdown by exact text match
    event_name: string like "200 Free SCY" (must match exactly)
    Returns True if successful, False otherwise
    """
    try:
        # Wait for dropdown to be present
        sleep(2)
        dropdown_element = driver.find_element(By.ID, "select_1")
        
        # Create Select object
        select = Select(dropdown_element)
        
        # Select by visible text (exact match)
        select.select_by_visible_text(event_name)
        sleep(1)  # Wait for page to update after selection
        
        return True
    except Exception as ex:
        print(f"Error selecting event '{event_name}' from dropdown: {ex}")
        return False


def click_event_progression_button(driver):
    """
    Clicks the EVENT PROGRESSION button/tab on the page
    Returns True if successful, False otherwise
    """
    try:
        # Wait for page to load
        sleep(2)
        
        # Try finding by text content first (most reliable)
        try:
            event_prog_button = driver.find_element(By.XPATH, "//button[contains(text(), 'EVENT PROGRESSION')]")
            event_prog_button.click()
            sleep(1)
            return True
        except:
            # Fallback: try by CSS selector
            try:
                event_prog_button = driver.find_element(By.CSS_SELECTOR, "li.c-tabs__item button.c-tabs__link")
                event_prog_button.click()
                sleep(0.5)
                return True
            except:
                # Fallback: try just the button class
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, "button.c-tabs__link")
                    for btn in buttons:
                        if "EVENT PROGRESSION" in btn.text:
                            btn.click()
                            sleep(1)
                            return True
                except:
                    pass
        
        print("ERROR: Could not find EVENT PROGRESSION button")
        return False
        
    except Exception as ex:
        print(f"Error clicking EVENT PROGRESSION button: {ex}")
        return False

######## the top are js utils



def check_event_progression(driver, event): ## returns fastest time
    ## event is a string in the format of "50 Free SCY"
    ##driver should be in event progression page -- need to first click dropdown to get desired event
    ## then search for the best time in the past TIMEEXPIRATION years and return it
    ## if no valid time, return None
    
    # Select the event from dropdown
    if not select_event_from_dropdown(driver, event):
        return None
    
    # Wait for table to load after selecting event
    sleep(2)
    
    # Find all rows in the progression table (simplified like scrapeprofile)
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    
    if len(rows) == 0:
        print(f"No rows found for event progression: {event}")
        return None
    
    valid_times = []
    
    for row in rows:
        all_cells = row.find_elements(By.CSS_SELECTOR, "td")
        
        if len(all_cells) < 4:  # Need at least 4 cells (time, empty, meet, date)
            continue
        
        try:
            # Based on debug output: Cell 0 = time, Cell 3 = date
            time_str = all_cells[0].text.strip()
            dt = all_cells[3].text.strip()
            
            if not dt or not time_str:
                continue
            
            # Check if date is valid
            if validdate(dt):
                time_seconds = parse_time_to_seconds(time_str)
                if time_seconds is not None:
                    valid_times.append({
                        "time": time_str,
                        "time_seconds": time_seconds,
                        "date": dt
                    })
        
        except Exception as ex:
            print(f"Error processing row: {ex}")
            continue
    
    # Find the fastest time (lowest seconds)
    if len(valid_times) == 0:
        return None
    
    fastest = min(valid_times, key=lambda x: x["time_seconds"])
    return fastest["time"]  # Return just the time string
    
def splitevent(event):

    ## event is a string in the format of "50 Free SCY"
    ## returns a tuple of (race, course)
    eventlist = event.split(' ')
    race = eventlist[0]+' '+eventlist[1]
    course = eventlist[2]
    return race, course

def scrapeprofile(driver): ## return scraped data from a page of one swimmer
    hmpgurl = driver.current_url
    # Only navigate if not already on times page
    if not hmpgurl.endswith('/times/'):
        driver.get(hmpgurl.rstrip('/') + '/times/')
    # Wait for table to load
    sleep(2)
    
    rows = driver.find_elements(By.CSS_SELECTOR, '#js-swimmer-profile-times-container tbody tr')
    
    if len(rows) == 0:
        print("ERROR: No rows found! The page might not have loaded or selector is wrong.")
        print(f"Current URL: {driver.current_url}")
        return ## might need to check what we're returning here
    
    info = []
    flagged_events = []
    for i, row in enumerate(rows):

        # Get all cells in the row
        all_cells = row.find_elements(By.CSS_SELECTOR, "td")
        
        try:
            ## get date - cell 4 (5th cell, index 4)
            dt = all_cells[4].text
        except Exception as ex:
            print(f"Error getting date: {ex}")
            continue
        
        try:
            ###### get event - cell 0 (first cell, index 0)
            event = all_cells[0].text
        except Exception as ex:
            print(f"Error getting event: {ex}")
            continue
        
        try:
            #### get time - cell 1 (second cell, index 1)
            time = all_cells[1].text
        except Exception as ex:
            print(f"Error getting time: {ex}")
            continue

        if validdate(dt):
            race, course = splitevent(event)
            info.append({"event": race, "course": course, "time": time})
        else:
            if ishsevent(event):
                flagged_events.append(event) ## you mighttt have to also append time and date idk tho
            else:
                continue
    

    ### now we deal with flagged events -- make new function for this
    if len(flagged_events) > 0:
        if click_event_progression_button(driver):
            # Process flagged events here
            for event in flagged_events:
                recent_time = check_event_progression(driver, event)
                if recent_time is not None:
                    race, course = splitevent(event)
                    info.append({"event": race, "course": course, "time": recent_time})
    return info


######## swimcloud search functions


def open_and_search(driver, query, enter=False):### opens swimcloud and searches for query
    driver.get('https://www.swimcloud.com/')
    # Wait for page to load
    sleep(1)
    searchbar = driver.find_element(By.ID, "global-search-select")
    searchbar.click()
    sleep(0.5)
    searchbar.clear()
    searchbar.send_keys(query)
    
    if enter:
        # Wait for search results dropdown to appear, then click first option
        sleep(2)
        first_result = driver.find_element(By.CSS_SELECTOR, '[role="option"]:first-child')
        first_result.click()
        sleep(2)  # Wait for page to navigate
    else:
        # Wait for search to process
        sleep(2)

def getallprofiles (driver, query):### gets the immediate search result lists of profiles (eg. Helen Chen WWP South)
    open_and_search(driver, query, enter=False)
    # Try to find results, but if nothing found, return empty list
    try:
        results = driver.find_elements(By.CSS_SELECTOR, '[role="option"]')
        texts = [r.text for r in results]
        return texts
    except:
        # Nothing found, return empty list
        return []

def searchprofile(driver, name):
    ## the only function you actually need to call- takes in a name and then returns all available swimcloud data on them
    ## prints warning in terminal if something seems wrong tho
    profs = getallprofiles(driver, name + ' ' + STATE)
    if len(profs) > 2:
        print(f"ERROR: Too many profiles found for {name} in {STATE}-- please manually check and flag if needed")
        SWIMCLOUD_PROBLEMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SWIMCLOUD_PROBLEMS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{name} {STATE}\n")
    elif len(profs) == 0:
        return None
    info = []
    for p in profs:
        profile = p.replace('\n', ' ')
        open_and_search(driver, profile, enter=True)
        # Wait for times table to load
        sleep(3)
        info.append({"profile": profile, "data": scrapeprofile(driver)})
    return info

def searchprofilev2(driver, urls, name):
    info = []
    for url in urls:
        driver.get(url)
        sleep(3)
        info.append(scrapeprofile(driver))
    return info

#ok this all works functionally now

def save_swimmer_to_mongodb(db, swimmer_data, year=None, team=None, profile=None, source='njcom'):
    """
    save a single swimmer's data to MongoDB
    merges new times with existing data, avoids duplicates
    
    Args:
        db: mongoDB database object
        swimmer_data: dictionary with 'swimmer' and 'data' keys
            - for njcom: 'data' is list of events with times (from scrapeDataForOneSwimmer)
            - for swimcloud: 'data' is flat list of dicts with 'event', 'course', 'time' (from scrapeprofile)
        year: season year (e.g., "2024-2025") - required for njcom
        team: Ttam name - required for njcom
        profile: profile name (e.g., "Jon Doe RandomTeam") - required for swimcloud
        source: Data source ('njcom' or 'swimcloud')
    
    Returns:
        dict with 'inserted' (bool), 'updated' (bool), 'new_times_count' (int)
    """
    collection = db[COLLECTION_NAME]
    
    # Handle swimcloud data transformation (flat list to grouped events)
    if source == 'swimcloud':
        if profile is None:
            raise ValueError("profile is required when source='swimcloud'")
        
        # Transform swimcloud data from flat list to grouped events format
        raw_data = swimmer_data.get('data', [])
        if raw_data is None:
            raw_data = []
        
        # Group by event name
        event_dict = {}
        for item in raw_data:
            event_name = item.get('event', '')
            if event_name not in event_dict:
                event_dict[event_name] = []
            
            # Convert swimcloud format to times array format
            # Note: swimcloud doesn't have location, so don't include it
            time_entry = {
                'time': item.get('time', '')
            }
            if 'course' in item:
                time_entry['course'] = item.get('course')
            
            event_dict[event_name].append(time_entry)
        
        # Convert to njcom-like structure
        transformed_data = []
        for event_name, times in event_dict.items():
            transformed_data.append({
                'event': event_name,
                'times': times
            })
        
        swimmer_data['data'] = transformed_data
    
    # Determine unique identifier based on source
    if source == 'njcom':
        if year is None or team is None:
            raise ValueError("year and team are required when source='njcom'")
        
        query_filter = {
            'swimmer': swimmer_data['swimmer'],
            'year': year,
            'team': team,
            'source': source
        }
    elif source == 'swimcloud':
        query_filter = {
            'swimmer': swimmer_data['swimmer'],
            'profile': profile,
            'source': source
        }
    else:
        raise ValueError("source must be 'njcom' or 'swimcloud'")
    
    # Check if swimmer already exists
    existing = collection.find_one(query_filter)
    
    if existing:
        # Merge new data with existing data
        existing_events = {event['event']: event for event in existing.get('data', [])}
        new_events = {event['event']: event for event in swimmer_data.get('data', [])}
        
        merged_data = []
        new_times_count = 0
        
        # Process all events (both existing and new)
        all_event_names = set(existing_events.keys()) | set(new_events.keys())
        
        for event_name in all_event_names:
            existing_event = existing_events.get(event_name)
            new_event = new_events.get(event_name)
            
            if existing_event and new_event:
                # Merge times, avoiding duplicates
                existing_times = existing_event.get('times', [])
                new_times = new_event.get('times', [])
                
                # Create a set for quick lookup
                # For njcom: use (time, location) since location matters
                # For swimcloud: use time only since there's no location field
                if source == 'swimcloud':
                    existing_time_set = {t.get('time', '') for t in existing_times}
                    # Add only new times that don't already exist
                    for new_time in new_times:
                        if new_time.get('time', '') not in existing_time_set:
                            existing_times.append(new_time)
                            new_times_count += 1
                else:  # njcom
                    existing_time_set = {(t.get('time', ''), t.get('location', '')) for t in existing_times}
                    # Add only new times that don't already exist
                    for new_time in new_times:
                        time_key = (new_time.get('time', ''), new_time.get('location', ''))
                        if time_key not in existing_time_set:
                            existing_times.append(new_time)
                            new_times_count += 1
                
                merged_data.append({
                    'event': event_name,
                    'times': existing_times
                })
            elif existing_event:
                # Keep existing event
                merged_data.append(existing_event)
            else:
                # New event, add all times
                merged_data.append(new_event)
                new_times_count += len(new_event.get('times', []))
        
        # Update with merged data
        swimmer_data['data'] = merged_data
        if source == 'njcom':
            swimmer_data['year'] = year
            swimmer_data['team'] = team
        elif source == 'swimcloud':
            swimmer_data['profile'] = profile
        swimmer_data['source'] = source
        
        result = collection.update_one(query_filter, {'$set': swimmer_data})
        
        return {
            'inserted': False,
            'updated': result.modified_count > 0,
            'new_times_count': new_times_count
        }
    else:
        # New swimmer, just insert
        if source == 'njcom':
            swimmer_data['year'] = year
            swimmer_data['team'] = team
        elif source == 'swimcloud':
            swimmer_data['profile'] = profile
        swimmer_data['source'] = source
        
        result = collection.insert_one(swimmer_data)
        
        total_times = sum(len(event.get('times', [])) for event in swimmer_data.get('data', []))
        
        return {
            'inserted': True,
            'updated': False,
            'new_times_count': total_times
        }
