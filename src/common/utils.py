import json
from pathlib import Path

# Path roots (stable no matter which cwd you run from)
COMMON_DIR = Path(__file__).resolve().parent
SRC_DIR = COMMON_DIR.parent
REPO_ROOT = SRC_DIR.parent

OFFICIAL_COLLECTION_NAME = "officialswimmerprofiles"
DB_NAME = "swimmeet"
COLLECTION_NAME = "swimmers"

# Scraped backup data lives under src/data/ (see .gitignore)
DATA_DIR = SRC_DIR / "data"
NJCOM_DATA_DIR = DATA_DIR / "njcom"
SWIMCLOUD_DATA_DIR = DATA_DIR / "swimcloud"
SWIMCLOUD_PROBLEMS_FILE = SWIMCLOUD_DATA_DIR / "problems.txt"

CONVERSIONS_FILE = COMMON_DIR / "conversions.json"

HSEVENTS = ['50 Free', '100 Free', '200 Free', '500 Free', '100 Back', '100 Breast', '100 Fly', '200 IM']

# Equivalent events across different courses (e.g., 500 Free SCY = 400 Free SCM/LCM)
EQUIVALENT_EVENTS = {
    "500 Free": "400 Free",      # 500 Free (SCY) = 400 Free (SCM/LCM)
    "400 Free": "500 Free",       # 400 Free (SCM/LCM) = 500 Free (SCY)
    "1000 Free": "800 Free",     # 1000 Free (SCY) = 800 Free (SCM/LCM)
    "800 Free": "1000 Free",     # 800 Free (SCM/LCM) = 1000 Free (SCY)
    "1650 Free": "1500 Free",    # 1650 Free (SCY) = 1500 Free (SCM/LCM)
    "1500 Free": "1650 Free",    # 1500 Free (SCM/LCM) = 1650 Free (SCY)
}
TIMEEXPIRATION = 2 # years -- how many before the last Nov 1st is a valid time

STATE = 'nj' # state to search for

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

def load_conversions():
    """Load conversion constants from JSON file
    helper function for convert_time_to_scy-- called nowhere else but there
    """
    try:
        with open(CONVERSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"warning: {CONVERSIONS_FILE} not found. check filepath is correct")
        return None
    except json.JSONDecodeError as e:
        print(f"Error reading {CONVERSIONS_FILE}: {e}")
        return None

def convert_time_to_scy(time_seconds, event, course):
    """
    convert a time string to scy equivalent using scraped conversions.
    
    Args:
        time_seconds: time in seconds (float) -- if in string use parse_time_to_seconds first
        event: Event name (e.g., "100 Free", "200 Fly")
        course: Source course ("SCY", "SCM", or "LCM")
    
    Returns:
        time in seconds (float) as SCY equivalent, or None if conversion fails
    """
    # check if time_seconds is None
    if time_seconds is None:
        return None
    
    # if already scy, no conversion needed
    if course == 'SCY':
        return time_seconds

    # load conversions
    conversions = load_conversions()
    if conversions is None:
        return None
    
    # get the conversion key (e.g., "LCM_to_SCY" or "SCM_to_SCY")
    conversion_key = f"{course}_to_SCY"
    if conversion_key not in conversions:
        print(f"Warning: No conversion found for {course} -> SCY")
        return None
    
    # get event conversions
    event_conversions = conversions[conversion_key]
    
    # try to find the event (exact match first, then try variations)
    conversion_config = None
    if event in event_conversions:
        conversion_config = event_conversions[event]
    else:
        # try to match with variations (e.g., "100 Free" vs "100 Free SCY")
        event_clean = event.split()[0] + " " + " ".join(event.split()[1:-1]) if len(event.split()) > 2 else event
        if event_clean in event_conversions:
            conversion_config = event_conversions[event_clean]
    
    if conversion_config is None:
        print(f"Warning: No conversion found for event '{event}' in {conversion_key}")
        return None
    
    # apply conversion based on type
    conversion_type = conversion_config.get('type', 'linear')
    if conversion_type == 'linear':
        multiplier = conversion_config.get('multiplier', 1.0)
        offset = conversion_config.get('offset', 0.0)
        return time_seconds * multiplier + offset
    else:
        print(f"Warning: Unknown conversion type '{conversion_type}'")
        return None

def format_time_from_seconds(seconds, include_hundredths=True):
    """
    convert time in seconds back to string format (e.g., 90.0 -> "1:30.00" or "1:30")
    
    Args:
        seconds: time in seconds (float)
        include_hundredths: If True, include hundredths (eg, "1:30.00"), 
                          if False, just minutes:seconds (eg, "1:30")
    
    Returns:
        time string in format "M:SS.mm" or "M:SS"
    """
    if seconds is None:
        return None
    
    minutes = int(seconds // 60)
    secs = seconds % 60
    
    if minutes > 0:
        if include_hundredths:
            return f"{minutes}:{secs:05.2f}"
        else:
            secs_int = int(secs)
            return f"{minutes}:{secs_int:02d}"
    else:
        # Less than a minute, just show seconds
        if include_hundredths:
            return f"{secs:.2f}"
        else:
            return f"{int(secs)}"