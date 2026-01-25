"""
Script to create officialswimmerprofiles collection
Merges all profiles for each swimmer and keeps only the fastest time per event
"""

from mongodb_helper import connect_to_mongodb, COLLECTION_NAME
from sconeswimmer import parse_time_to_seconds, EQUIVALENT_EVENTS, HSEVENTS
import json
import os

CONVERSIONS_FILE = "scraped_conversions.json"
OFFICIAL_COLLECTION_NAME = "officialswimmerprofiles"

# Cache for loaded conversions
_conversions_cache = None

def load_conversions():
    """Load conversion constants from JSON file"""
    global _conversions_cache
    if _conversions_cache is not None:
        return _conversions_cache
    
    file_path = os.path.join(os.path.dirname(__file__), CONVERSIONS_FILE)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            _conversions_cache = json.load(f)
        return _conversions_cache
    except FileNotFoundError:
        print(f"Warning: {CONVERSIONS_FILE} not found. Cannot convert times.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error reading {CONVERSIONS_FILE}: {e}")
        return None

def convert_time_to_scy(time_seconds, event, course):
    """
    Convert a time string to SCY (Short Course Yards) equivalent using scraped conversions.
    
    Args:
        time_seconds: Time in seconds (float) -- if in string use parse_time_to_seconds first
        event: Event name (e.g., "100 Free", "200 Fly")
        course: Source course ("SCY", "SCM", or "LCM")
    
    Returns:
        Time in seconds (float) as SCY equivalent, or None if conversion fails
    """
    # If already SCY, no conversion needed
    if course == 'SCY':
        return time_seconds

    # Load conversions
    conversions = load_conversions()
    if conversions is None:
        return None
    
    # Get the conversion key (e.g., "LCM_to_SCY" or "SCM_to_SCY")
    conversion_key = f"{course}_to_SCY"
    if conversion_key not in conversions:
        print(f"Warning: No conversion found for {course} -> SCY")
        return None
    
    # Get event conversions
    event_conversions = conversions[conversion_key]
    
    # Try to find the event (exact match first, then try variations)
    conversion_config = None
    if event in event_conversions:
        conversion_config = event_conversions[event]
    else:
        # Try to match with variations (e.g., "100 Free" vs "100 Free SCY")
        event_clean = event.split()[0] + " " + " ".join(event.split()[1:-1]) if len(event.split()) > 2 else event
        if event_clean in event_conversions:
            conversion_config = event_conversions[event_clean]
    
    if conversion_config is None:
        print(f"Warning: No conversion found for event '{event}' in {conversion_key}")
        return None
    
    # Apply conversion based on type
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
    Convert time in seconds back to string format (e.g., 90.0 -> "1:30.00" or "1:30")
    
    Args:
        seconds: Time in seconds (float)
        include_hundredths: If True, include hundredths (e.g., "1:30.00"), 
                          if False, just minutes:seconds (e.g., "1:30")
    
    Returns:
        Time string in format "M:SS.mm" or "M:SS"
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

def get_best_time_from_swimmer(collection, swimmer, event): ## works functionally
    """
    MAKE SURE THE COLLECTION IS "SWIMMERS"
    Get the fastest time for a swimmer and event across all their documents.
    Converts all non-SCY times to SCY for comparison.
    
    Args:
        collection: MongoDB collection object
        swimmer: Name of the swimmer
        event: Event name (e.g., "100 Free", "200 Fly")
    
    Returns:
        Fastest time in seconds (float) as SCY equivalent, or None if no times found
    """
    # Get all documents for this swimmer (all years, teams, sources)
    swimmer_docs = list(collection.find({"swimmer": swimmer}))
    
    if not swimmer_docs:
        return None
    
    # Collect all times for this event
    all_times_scy = []
    
    for doc in swimmer_docs:
        data = doc.get('data', [])
        if data is None or len(data) == 0:
            continue

        # Find the event in this document's data
        for event_data in data:
            event_name = event_data.get('event', '')
            
            # Check if this event matches (including equivalent events)
            # e.g., if looking for "500 Free", also match "400 Free"
            event_matches = (event_name == event)
            if not event_matches and event in EQUIVALENT_EVENTS:
                # Check if document event is the equivalent
                equivalent_event = EQUIVALENT_EVENTS[event]
                event_matches = (event_name == equivalent_event)
            
            if not event_matches:
                continue
            
            # Process all times for this event
            times = event_data.get('times', [])
            for time_entry in times:
                time_str = time_entry.get('time', '')
                if not time_str:
                    continue
                
                # Parse time to seconds
                time_seconds = parse_time_to_seconds(time_str)
                if time_seconds is None:
                    continue
                
                # Get course (default to SCY if not specified)
                course = time_entry.get('course', 'SCY')
                
                # Convert to SCY - use requested event (conversion is same for equivalent events)
                time_scy = convert_time_to_scy(time_seconds, event, course)
                if time_scy is not None:
                    all_times_scy.append(time_scy)
    
    # Return the fastest time (lowest value)
    if not all_times_scy:
        return None
    
    return min(all_times_scy)

def get_seasons_and_teams(collection, swimmer):
    """
    Get a dict mapping season (year) to team for a swimmer based on nj.com documents.
    Only includes seasons where the swimmer has non-empty data.
    
    This dict should be stored in the official profile document as a "teams" field
    to enable efficient queries like: find({"teams.2025-2026": "Lawrence"})
    
    Args:
        collection: MongoDB collection object (should be "swimmers" collection)
        swimmer: Name of the swimmer
    
    Returns:
        Dict with format {season: team} for each season with data, or empty dict if none found
        Example: {"2024-2025": "Hightstown", "2025-2026": "Princeton"}
    """
    # Query for all nj.com documents for this swimmer
    swimmer_docs = list(collection.find({
        "swimmer": swimmer,
        "source": "njcom"
    }))
    
    if not swimmer_docs:
        return {}
    
    seasons_teams = {}
    
    for doc in swimmer_docs:
        # Check if data exists and is not empty
        data = doc.get('data', [])
        if data is None or len(data) == 0:
            continue
        
        # Extract season (year) and team
        year = doc.get('year')
        team = doc.get('team')
        
        # Only add if both year and team exist
        if year and team:
            seasons_teams[year] = team
    
    return seasons_teams


def findallbesttimes(collection, swimmer):
    """
    Find the best time for each event for each swimmer
    """
    best_times = {}
    for event in HSEVENTS:
        best_times[event] = get_best_time_from_swimmer(collection, swimmer, event)
    return best_times



