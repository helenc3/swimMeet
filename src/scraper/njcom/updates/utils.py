from selenium.webdriver.common.by import By
from urllib.parse import urljoin
from common.utils import parse_time_to_seconds, HSEVENTS, convert_time_to_scy
import csv
import os
from datetime import datetime
from pathlib import Path

UPDATES_DIR = Path(__file__).resolve().parent
ERRORS_PATH = UPDATES_DIR / "errorevents"


"""
this is the new version of scrpingUtils. 
- updates current data w new meet results. 
- needs current data to work
- util functions for scraping data from the web.
- methods here used in main.py, fixerrors.py -- both in this directory
- IMPORTANT: if swimmer found on nj.com not found in existing database, no update is made.
"""

SKIPPED_EVENTS = ["200 MR", "200 FR", "400 FR"]
SCHEDULE_URL = "https://highschoolsports.nj.com/girlsswimming/schedule/"
TIMEDELTA_BETWEEN_GAMES = 2

def write_result_to_csv(result, datestr, teams):
    """
    this method is used to write events with possible errors to a csv file. 
    Writes a result hashmap to a CSV file in the ERRORS_PATH directory.
    
    args:
        result: hashmap with structure:
            {
                "event": "200 Free",
                "course": "SCM",
                "data": [
                    {"place": 1, "name": "...", "team": "...", "time": "2:19.45"},
                    ...
                ]
            }
    
    returns:
        str: path to the created csv file, or None if error
    """
    if not result or "event" not in result or "data" not in result:
        print("Invalid result dictionary provided")
        return None
    
    # Create directory if it doesn't exist
    os.makedirs(ERRORS_PATH, exist_ok=True)
    
    # Generate filename based on event name and timestamp
    event_name = result.get("event", "unknown_event").replace(" ", "_")
    course = result.get("course", "unknown_course")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Truncate team names to first 5 characters
    team1 = teams[0][:5] if teams and len(teams) > 0 else "none"
    team2 = teams[1][:5] if teams and len(teams) > 1 else "none"
    filename = f"{event_name}_{course}_{datestr}_{team1}_{team2}_unverified.csv"
    filepath = os.path.join(ERRORS_PATH, filename)
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Place', 'Name', 'Team', 'Time', 'Event', 'Course']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for entry in result["data"]:
                writer.writerow({
                    'Place': entry.get("place", ""),
                    'Name': entry.get("name", ""),
                    'Team': entry.get("team", ""),
                    'Time': entry.get("time", ""),
                    'Event': result.get("event", ""),
                    'Course': result.get("course", "")
                })
        
        print(f"result written to csv: {filepath}")
        return filepath
    except Exception as e:
        print(f"error writing result to csv: {e}")
        return None

def parseeventname(event_name):
    """
    parses the event name from the event card. Example: "200 Free (meters)" -> 200 Free, SCM
    """
    try:
        event, course = event_name.split(" (")
        event = event.strip()
        course = course.strip(")")
        if course == "meters":
            course = "SCM"
        elif course == "yards":
            course = "SCY"
        else:
            raise ValueError(f"Unknown course: {course}")
        return event, course
    except Exception as e:
        print(f"Error parsing event name: {e}")
        return None, None

def verifycard(result):
    """
    Verifies that times and places correspond correctly in the scraped data.
    
    Args:
        result: Dictionary returned by scrapeOneCard with structure:
            {
                "event": "200 Free",
                "course": "SCM",
                "data": [
                    {"place": 1, "name": "...", "team": "...", "time": "2:19.45"},
                    ...
                ]
            }
    
    Returns:
        dict: same hashmap structure with times converted to SCY seconds and course set to "SCY"
        None: if validation fails (raises error)
    
    Raises:
        ValueError: if validation fails (missing place, times out of order, or missing places)
    """
    event = result["event"]
    course = result["course"]
    
    # Check 1: No time should have None place
    for data in result["data"]:
        if data["place"] is None:
            raise ValueError(f"Found entry with no place (None) for event {event}")
    
    # Get all places and check for missing places
    places = sorted([data["place"] for data in result["data"]])
    
    # Check 2: Places should be consecutive (no gaps like 1, 3 without 2)
    if places:
        expected_places = list(range(1, len(places) + 1))
        if places != expected_places:
            missing = set(expected_places) - set(places)
            raise ValueError(f"Missing places in event {event}: {sorted(missing)}")
    
    # Convert all times to seconds, then to SCY
    converted_data = []
    for data in result["data"]:
        time_str = data["time"]
        try:
            time_sec = parse_time_to_seconds(time_str)
            time_scy = convert_time_to_scy(time_sec, event, course)
            converted_data.append({
                "place": data["place"],
                "name": data["name"],
                "team": data["team"],
                "time": time_scy
            })
        except Exception as e:
            raise ValueError(f"Error converting time '{time_str}' for place {data['place']} in event {event}: {e}")
    
    # Sort by place to ensure correct order for time comparison
    converted_data.sort(key=lambda x: x["place"])
    
    # Check 3: Times should be in order (1st place fastest, 2nd slower, etc.)
    for i in range(len(converted_data) - 1):
        current_place = converted_data[i]["place"]
        next_place = converted_data[i + 1]["place"]
        current_time = converted_data[i]["time"]
        next_time = converted_data[i + 1]["time"]
        
        if current_time is None or next_time is None:
            raise ValueError(f"Found None time in event {event} at place {current_place if current_time is None else next_place}")
        
        if current_time > next_time:
            raise ValueError(f"Times out of order in event {event}: place {current_place} ({current_time}s) is slower than place {next_place} ({next_time}s)")
    
    # All checks passed - return converted result
    return {
        "event": event,
        "course": "SCY",
        "data": converted_data
    }

def scrapeOneCard(card_element):
    """
    Scrapes one event card from Swimcloud meet results page.
    
    Args:
        card_element: Selenium WebElement representing a div.card containing event data
    
    Returns:
        dict: {
            "event": "200 Free (meters)",
            "data": [
                {
                    "place": 1,
                    "name": "Elizabeth Molinelli",
                    "team": "Hightstown",
                    "time": "2:19.45"
                },
                ...
            ]
        }
    """
    result = {
        "event": "",
        "course": "",
        "data": []
    }
    
    try:
        # Extract event name from h2.card-title
        # First check if this card actually has an event title (skip non-event cards)
        try:
            event_title = card_element.find_element(By.CSS_SELECTOR, "h2.card-title")
        except Exception:
            # This card doesn't have an event title, skip it (likely a header/nav card)
            return None
        
        event, course = parseeventname(event_title.text.strip())
        if event is None or course is None:
            return None
        if event in SKIPPED_EVENTS:
            return None
        result["event"] = event
        result["course"] = course
    except Exception as e:
        # If we can't parse the event name, skip this card
        print(f"Error extracting event name: {e}")
        return None
    
    try:
        # Find the table inside the card
        table = card_element.find_element(By.CSS_SELECTOR, "table.table")
        tbody = table.find_element(By.TAG_NAME, "tbody")
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        
        for row in rows:
            try:
                tds = row.find_elements(By.TAG_NAME, "td")
                if len(tds) < 4:
                    continue
                
                # Place: first td with text-center
                place_text = tds[0].text.strip() if tds[0].text else ""
                if not place_text:
                    place = None
                else:
                    try:
                        place = int(place_text)
                    except ValueError:
                        place = place_text  # Keep as string if not a number
                
                # Team and Name: in the td with text-left (usually tds[2])
                # Team is in strong tag, Name is in a tag
                team = ""
                name = ""
                for td in tds:
                    td_class = td.get_attribute("class") or ""
                    if "text-left" in td_class:
                        try:
                            strong_tag = td.find_element(By.TAG_NAME, "strong")
                            team = strong_tag.text.strip()
                        except:
                            pass
                        try:
                            a_tag = td.find_element(By.TAG_NAME, "a")
                            name = a_tag.text.strip()
                        except:
                            pass
                        break
                
                # Time: last td with text-center
                time_text = tds[-1].text.strip()
                
                if name:  # Only add if we found a name
                    result["data"].append({
                        "place": place,
                        "name": name,
                        "team": team,
                        "time": time_text
                    })
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
                
    except Exception as e:
        print(f"Error extracting table data: {e}")
    
    return result

def scrapeOneMeet(driver, date):
    """
    Scrapes all events from a meet results page.
    
    Args:
        driver: Selenium WebDriver instance
        date: datetime.date object
    
    Returns:
        dict: {
            "date": "YYYY-MM-DD",
            "teams": ["Team1", "Team2"],
            "data": [verified_result1, verified_result2, ...]
        }
    """
    events = driver.find_elements(By.CSS_SELECTOR, "div.card")

    data = {"date": "", "teams": [], "data": []}
    data["date"] = date.strftime("%Y-%m-%d")
    
    # Extract teams from the first card (usually events[0]) which contains the teams table
    if events:
        try:
            first_card = events[0]
            # Find all team names in <p class="lead"> tags within table cells
            team_elements = first_card.find_elements(By.CSS_SELECTOR, 'table p.lead')
            for team_elem in team_elements:
                team_text = team_elem.text.strip()
                if team_text:
                    # Extract team name (remove win-loss record if present)
                    # e.g., "Watchung Hills (6-4)" -> "Watchung Hills"
                    team_name = team_text.split('(')[0].strip()
                    if team_name:
                        data["teams"].append(team_name)
                        
        except Exception as e:
            print(f"Error extracting teams: {e}")

    for event in events:
        result = scrapeOneCard(event)
        if result is None:
            continue
        try:
            verified_result = verifycard(result)
            data["data"].append(verified_result)
        except Exception as e:
            print(f"Error verifying card: {e}")
            write_result_to_csv(result, data["date"], data["teams"])
            continue
    
    return data

def getdayurl(date):
    ## date is a datetime object
    month = date.month  # int, no leading zero (e.g., 2 for February)
    day = date.day      # int, no leading zero (e.g., 5 for 5th)
    year = date.year    # int (e.g., 2025)
    return SCHEDULE_URL + f"{year}/{month}/{day}"

def getgameurl(box):
    try:
        # Find the "Box Score" or "View Game Result" link within this box
        # Look for link with href containing "/game/"
        game_link = box.find_element(By.CSS_SELECTOR, 'a[href*="/game/"]')
        href = game_link.get_attribute("href")
        
        if href:
            # Convert relative URL to absolute if needed
            if href.startswith("/"):
                full_url = urljoin("https://highschoolsports.nj.com", href)
            elif href.startswith("http"):
                # Already an absolute URL
                full_url = href
            else:
                # Invalid URL format
                return None
            return full_url
    except Exception as e:
        return None


def getonedayurls(driver, date, conferences):
    url = getdayurl(date)
    driver.get(url)
    
    # Give page a moment to load, then find schedule boxes
    
    try:
        # Find all schedule boxes (no wait - returns immediately, empty list if none found)
        schedule_boxes = driver.find_elements(By.CSS_SELECTOR, 'div.sked-col[data-filter-conference]')
        
        # If no boxes found, return None immediately
        if not schedule_boxes:
            return None
        
        # Filter boxes based on selected conferences
        # Each box has data-filter-conference attribute that may contain multiple conferences separated by |
        game_urls = []
        for box in schedule_boxes:
            box_conferences = box.get_attribute("data-filter-conference")
            if box_conferences:
                # Split by | to get individual conferences
                box_conference_list = [c.strip() for c in box_conferences.split("|")]
                # Check if any of the requested conferences match this box
                if any(conf in box_conference_list for conf in conferences):
                    url = getgameurl(box)
                    if url is not None:
                        game_urls.append(url)
        
        # Only return None if NONE of the boxes match the requested conferences
        if not game_urls:
            return None
        return game_urls
      
    except Exception as e:
        return None
    
    
def save_meet_data_to_mongodb(event_results, collection):
    """
    Saves meet data to MongoDB and updates best times for swimmers.
    
    For each time swum, finds the corresponding swimmer in the database.
    if swimmer is found and the time is faster than existing best time (or doesn't exist),
    updates the best_times field in officialswimmerprofiles collection.
    
    Args:
        event_results: List of event results from scrapeOneMeet with structure:
            [
                {
                    "event": "200 Free",
                    "course": "SCY",
                    "data": [
                        {"place": 1, "name": "John Doe", "team": "Team1", "time": 120.5},
                        ...
                    ]
                },
                ...
            ]
        collection: MongoDB collection object (officialswimmerprofiles)
    
    Returns:
        dict: {
            "swimmers_found": int,
            "swimmers_updated": int,
            "swimmers_not_found": int
        }
    """
    stats = {
        "swimmers_found": 0,
        "swimmers_updated": 0,
        "swimmers_not_found": 0
    }
    
    try:
        # iterate through each event
        for event_result in event_results:
            event_name = event_result.get("event", "")
            
            # skip if not an HS event
            if event_name not in HSEVENTS:
                continue
            
            # iterate through each swimmer result in the event
            for swimmer_result in event_result.get("data", []):
                swimmer_name = swimmer_result.get("name", "").strip()
                new_time = swimmer_result.get("time")
                
                if not swimmer_name or new_time is None:
                    continue
                
                # Find swimmer in database
                swimmer_doc = collection.find_one({"swimmer": swimmer_name})
                
                if not swimmer_doc:
                    stats["swimmers_not_found"] += 1
                    continue
                
                stats["swimmers_found"] += 1
                
                # get current best_times
                best_times = swimmer_doc.get("best_times", {})
                current_best = best_times.get(event_name)
                
                # update if new time is faster or if no current best time exists
                should_update = False
                if current_best is None:
                    should_update = True
                elif new_time < current_best:
                    should_update = True
                
                if should_update:
                    # update the best time
                    collection.update_one(
                        {"swimmer": swimmer_name},
                        {"$set": {f"best_times.{event_name}": new_time}}
                    )
                    stats["swimmers_updated"] += 1
                    print(f"Updated {swimmer_name}'s {event_name}: {current_best} -> {new_time}")
        
        return stats
        
    except Exception as e:
        print(f"error saving meet data to MongoDB: {e}")
        return stats

