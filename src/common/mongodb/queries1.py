
from common.utils import COLLECTION_NAME
from common.utils import parse_time_to_seconds, EQUIVALENT_EVENTS, HSEVENTS, convert_time_to_scy

"""
query functions for the older collection, COLLECTION_NAME
"""

def get_all_swimmers_with_event(db, event_name, year=None, team=None, source=None):
    """
    Get all swimmers who have times for a specific event
    Example: get_all_swimmers_with_event(db, "100 Fly", year="2024-2025")

    args:
        db: database object
        event_name: name of the event
        year: year of the event
        team: team of the swimmer
        source: source of the data

    returns:
        list of swimmers with times for the event
        eg. [{'swimmer': 'John Doe', 'team': 'Team A', 'year': '2024-2025', 'source': 'source1', 'event': '100 Fly', 'times': [100.0, 100.0, 100.0]}]
    """
    collection = db[COLLECTION_NAME]
    
    query = {"data.event": event_name}  # Query nested array
    if year:
        query["year"] = year
    if team:
        query["team"] = team
    if source:
        query["source"] = source
    
    swimmers = collection.find(query)
    
    results = []
    for swimmer in swimmers:
        # Extract just the event data from nested array
        event_data = [event for event in swimmer.get('data', []) if event.get('event') == event_name]
        if event_data:
            results.append({
                "swimmer": swimmer['swimmer'],
                "team": swimmer.get('team'),
                "year": swimmer.get('year'),
                "source": swimmer.get('source'),
                "event": event_name,
                "times": event_data[0].get('times', [])
            })
    
    return results

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

def get_all_times_for_event(collection, swimmer, event): ## works functionally
    """
    returns all times for an event for a swimmer
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

    return all_times_scy

def find_document_with_time(collection, swimmer, event, time_seconds, tolerance=0.01):
    """
    Find the document(s) containing a specific time for a swimmer and event.
    
    Args:
        collection: MongoDB collection object
        swimmer: Name of the swimmer
        event: Event name (e.g., "100 Free", "200 Fly")
        time_seconds: Time in seconds (float) to search for
        tolerance: Tolerance for time matching (default 0.01 seconds)
    
    Returns:
        List of dicts with keys: "source" (always), and "year", "team" (if source is "njcom")
        Example: [{"source": "njcom", "year": "2024-2025", "team": "Hightstown"}, 
                  {"source": "swimcloud"}]
    """
    # Get all documents for this swimmer
    swimmer_docs = list(collection.find({"swimmer": swimmer}))
    
    if not swimmer_docs:
        return []
    
    matching_docs = []
    processed_docs = set()  # Track which docs we've already processed
    
    for doc in swimmer_docs:
        # Create a unique identifier for this doc to avoid duplicates
        doc_id = (doc.get("source"), doc.get("year"), doc.get("team"))
        if doc_id in processed_docs:
            continue
        
        data = doc.get('data', [])
        if data is None or len(data) == 0:
            continue
        
        # Find the event in this document's data
        found_match = False
        for event_data in data:
            event_name = event_data.get('event', '')
            
            # Check if this event matches (including equivalent events)
            event_matches = (event_name == event)
            if not event_matches and event in EQUIVALENT_EVENTS:
                # Check if document event is the equivalent
                equivalent_event = EQUIVALENT_EVENTS[event]
                event_matches = (event_name == equivalent_event)
            
            if not event_matches:
                continue
            
            # Check all times for this event
            times = event_data.get('times', [])
            for time_entry in times:
                time_str = time_entry.get('time', '')
                if not time_str:
                    continue
                
                # Parse time to seconds
                entry_time_seconds = parse_time_to_seconds(time_str)
                if entry_time_seconds is None:
                    continue
                
                # Get course (default to SCY if not specified)
                course = time_entry.get('course', 'SCY')
                
                # Convert to SCY for comparison (use requested event for conversion)
                entry_time_scy = convert_time_to_scy(entry_time_seconds, event, course)
                if entry_time_scy is None:
                    continue
                
                # Check if times match within tolerance (both in SCY)
                if abs(entry_time_scy - time_seconds) <= tolerance:
                    # Extract only the fields we need
                    result = {
                        "source": doc.get("source", "unknown")
                    }
                    # Add year and team if source is njcom
                    if doc.get("source") == "njcom":
                        result["year"] = doc.get("year")
                        result["team"] = doc.get("team")
                    matching_docs.append(result)
                    processed_docs.add(doc_id)
                    found_match = True
                    break  # Found a match in this document, no need to check more times
            
            if found_match:
                break  # Already found match, don't check other events
    
    return matching_docs


def get_all_events_for_swimmer(collection, swimmer):
    """
    Get all unique events for a swimmer across all their documents.
    
    Args:
        collection: MongoDB collection object
        swimmer: Name of the swimmer
    
    Returns:
        Set of event names
    """
    swimmer_docs = list(collection.find({"swimmer": swimmer}))
    
    if not swimmer_docs:
        return set()
    
    events = set()
    
    for doc in swimmer_docs:
        data = doc.get('data', [])
        if not data:
            continue
        
        for event_data in data:
            event_name = event_data.get('event', '')
            if event_name:
                events.add(event_name)
    
    return events