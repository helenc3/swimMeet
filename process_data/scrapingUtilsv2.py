from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import re
from createswimmerprofsutils import convert_time_to_scy
from sconeswimmer import parse_time_to_seconds
import csv
import os
from datetime import datetime

SKIPPED_EVENTS = ["200 MR", "200 FR", "400 FR"]
ERRORS_PATH = "/Users/helenchen/workspace/swimMeet/process_data/errorevents"

def write_result_to_csv(result):
    """
    Writes a result dictionary to a CSV file in the ERRORS_PATH directory.
    
    Args:
        result: Dictionary with structure:
            {
                "event": "200 Free",
                "course": "SCM",
                "data": [
                    {"place": 1, "name": "...", "team": "...", "time": "2:19.45"},
                    ...
                ]
            }
    
    Returns:
        str: Path to the created CSV file, or None if error
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
    filename = f"{event_name}_{course}_{timestamp}_unverified.csv"
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
        
        print(f"Result written to CSV: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error writing result to CSV: {e}")
        return None

def parseeventname(event_name):
    """
    Parses the event name from the event card. Example: "200 Free (meters)" -> 200 Free, SCM
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

def format_verified_result(verified_result):
    """
    Formats a verified result dictionary into a nice readable string.
    
    Args:
        verified_result: Dictionary returned by verifycard
    
    Returns:
        str: Formatted string representation
    """
    if not verified_result:
        return "No result to format"
    
    event = verified_result["event"]
    course = verified_result["course"]
    data = verified_result["data"]
    

    
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"Event: {event} ({course})")
    output.append(f"{'='*60}")
    output.append(f"{'Place':<8} {'Name':<30} {'Team':<20} {'Time':<12}")
    output.append(f"{'-'*60}")
    
    for entry in data:
        place = entry["place"]
        name = entry["name"][:28]  # Truncate if too long
        team = entry["team"][:18]  # Truncate if too long
        time_str = entry["time"]
        output.append(f"{place:<8} {name:<30} {team:<20} {time_str:<12}")
    
    output.append(f"{'='*60}\n")
    return "\n".join(output)

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
        dict: Same structure with times converted to SCY seconds and course set to "SCY"
        None: If validation fails (raises error)
    
    Raises:
        ValueError: If validation fails (missing place, times out of order, or missing places)
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
        except:
            # This card doesn't have an event title, skip it (likely a header/nav card)
            return None
        
        event, course = parseeventname(event_title.text.strip())
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

def scrapeOneMeet(driver):
    events = driver.find_elements(By.CSS_SELECTOR, "div.card")
    for event in events:
        result = scrapeOneCard(event)
        if result is None:
            continue
        try:
            verified_result = verifycard(result)
            if verified_result is not None:
                print(format_verified_result(verified_result))
            else:
                print(f"Error verifying card: {result}")
        except Exception as e:
            print(f"Error verifying card: {e}")
            write_result_to_csv(result)
            continue
        

url = "https://highschoolsports.nj.com/game/1091442"
driver = webdriver.Chrome()
driver.get(url)
scrapeOneMeet(driver)
driver.quit()