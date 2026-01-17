from selenium import webdriver
from time import sleep
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from datetime import datetime, date
import re


HSEVENTS = ['50 Free', '100 Free', '200 Free', '500 Free', '400 Free', '100 Back', '100 Breast', '100 Fly', '200 IM']
TIMEEXPIRATION = 2 # years -- how many before the last Nov 1st is a valid time

def ishsevent(event):
    ###### return True if the event is a HS event, False otherwise
    ##### input is a string in the format of "50 Free SCY"
    race, course = splitevent(event)
    if race in HSEVENTS:
        return True
    else:
        return False

def validdate(date_str): 
    """
    date_str is a string in the format of "Jan 23, 2025"
    Returns True if the date is within TIMEEXPIRATION years to the last November 1st that occurred, False otherwise
    """
    try:
        # Parse the date string using datetime
        # Format: "Jan 23, 2025" -> "%b %d, %Y"
        parsed_date = datetime.strptime(date_str.strip(), "%b %d, %Y").date()
        
        # Get current date
        today = date.today()
        
        # Find the last November 1st that occurred
        # If we're in Nov or Dec, last Nov 1st is this year's Nov 1
        # Otherwise, last Nov 1st is last year's Nov 1
        if today.month >= 11:  # November or December
            last_nov_1 = date(today.year, 11, 1)
        else:  # January through October
            last_nov_1 = date(today.year - 1, 11, 1)
        
        # Calculate Nov 1st of TIMEEXPIRATION years before the last Nov 1st
        nov_1_expiration_years_ago = date(last_nov_1.year - TIMEEXPIRATION, 11, 1)
        
        # Check if date is between Nov 1st (TIMEEXPIRATION years ago) and last Nov 1st
        return nov_1_expiration_years_ago <= parsed_date <= last_nov_1
        
    except (ValueError, AttributeError):
        # If date parsing fails, return False
        return False


def select_event_from_dropdown(driver, event_name):
    """
    Selects an event from the dropdown by exact text match
    event_name: string like "200 Free SCY" (must match exactly)
    Returns True if successful, False otherwise
    """
    try:
        # Wait for dropdown to be present
        wait = WebDriverWait(driver, 10)
        dropdown_element = wait.until(
            EC.presence_of_element_located((By.ID, "select_1"))
        )
        
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
        # Wait for page to load and try multiple selectors
        wait = WebDriverWait(driver, 10)
        
        # Try finding by text content first (most reliable)
        try:
            event_prog_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'EVENT PROGRESSION')]"))
            )
            event_prog_button.click()
            sleep(1)
            return True
        except:
            # Fallback: try by CSS selector
            try:
                event_prog_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "li.c-tabs__item button.c-tabs__link"))
                )
                event_prog_button.click()
                sleep(1)
                return True
            except:
                # Fallback: try just the button class
                try:
                    event_prog_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.c-tabs__link"))
                    )
                    # Check if it's the right button by text
                    if "EVENT PROGRESSION" in event_prog_button.text:
                        event_prog_button.click()
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








def parse_time_to_seconds(time_str):
    """
    Converts time string (e.g., "1:45.23" or "45.23") to total seconds for comparison
    Returns float seconds, or None if parsing fails
    """
    try:
        time_str = time_str.strip()
        # Handle format like "1:45.23" (minutes:seconds.milliseconds)
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            # Handle format like "45.23" (just seconds)
            return float(time_str)
    except:
        return None


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
    driver.get(hmpgurl + 'times/')
    sleep(1) 
    
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


#ok this all works functionally now
