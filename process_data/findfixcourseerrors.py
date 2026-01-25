from mongodb_helper import connect_to_mongodb, COLLECTION_NAME
from sconeswimmer import parse_time_to_seconds, EQUIVALENT_EVENTS, HSEVENTS
from createswimmerprofs import convert_time_to_scy, get_best_time_from_swimmer
import json
import os
import numpy as np

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

def find_outliers(times, method='iqr', factor=1.5):
    """
    Find outliers in a list of times (in seconds).
    
    Args:
        times: List of times in seconds (floats)
        method: Method to use for outlier detection
            - 'iqr': Interquartile Range method (default) - values outside Q1-1.5*IQR or Q3+1.5*IQR
            - 'zscore': Z-score method - values with z-score > 2 standard deviations
        factor: Multiplier for IQR method (default 1.5, higher = more lenient)
    
    Returns:
        List of dictionaries with keys: "value" (outlier time), "type" ("high" or "low")
        Example: [{"value": 90.0, "type": "high"}, {"value": 50.0, "type": "low"}]
        If input has <= 2 entries, returns empty list (need at least 3 to detect outliers)
    """
    if len(times) <= 2:
        return []
    
    times = np.array(times)
    outliers = []
    
    if method == 'iqr':
        # Interquartile Range method
        Q1 = np.percentile(times, 25)
        Q3 = np.percentile(times, 75)
        IQR = Q3 - Q1
        
        # Define bounds
        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR
        
        # Find outliers (values outside the bounds)
        for i, time_val in enumerate(times):
            if time_val < lower_bound:
                outliers.append({"value": float(time_val), "type": "low"})
            elif time_val > upper_bound:
                outliers.append({"value": float(time_val), "type": "high"})
        
    elif method == 'zscore':
        # Z-score method
        mean = np.mean(times)
        std = np.std(times)
        
        if std == 0:  # All times are the same
            return []
        
        for i, time_val in enumerate(times):
            z_score = (time_val - mean) / std
            if abs(z_score) > 2:
                outlier_type = "high" if z_score > 0 else "low"
                outliers.append({"value": float(time_val), "type": outlier_type})
        
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr' or 'zscore'")
    
    return outliers

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

def find_all_outliers_for_swimmer(collection, swimmer, method='iqr', factor=1.5):
    """
    Find all outlier times for a swimmer across all high school events (HSEVENTS).
    
    Args:
        collection: MongoDB collection object
        swimmer: Name of the swimmer
        method: Method to use for outlier detection ('iqr' or 'zscore')
        factor: Multiplier for IQR method (default 1.5)
    
    Returns:
        List of dictionaries with keys: "event", "outliers" (list of outlier dicts)
        Example: [
            {
                "event": "100 Free",
                "outliers": [
                    {"value": 90.0, "type": "high"},
                    {"value": 50.0, "type": "low"}
                ]
            },
            ...
        ]
    """
    results = []
    
    # Check each high school event for outliers
    for event in HSEVENTS:
        # Get all times for this event (already converted to SCY)
        times = get_all_times_for_event(collection, swimmer, event)
        
        if times is None or len(times) == 0:
            continue
        
        # Get the best time for this event
        best_time = get_best_time_from_swimmer(collection, swimmer, event)
        
        # Find outliers
        outliers = find_outliers(times, method=method, factor=factor)
        
        # Only add to results if there are outliers
        if outliers:
            # Add document information for each outlier and filter
            outliers_with_docs = []
            for outlier in outliers:
                # Skip "high" type outliers (unusually fast times)
                if outlier["type"] == "high":
                    continue
                
                outlier_value = outlier["value"]
                
                # Only include if this outlier is the best time (within tolerance)
                if best_time is None or abs(outlier_value - best_time) > 0.01:
                    continue
                
                # Find which document(s) contain this time
                docs = find_document_with_time(collection, swimmer, event, outlier_value, tolerance=0.01)
                
                # Skip if any document is from swimcloud
                if any(doc.get("source") == "swimcloud" for doc in docs):
                    continue
                
                outlier_with_docs = outlier.copy()
                outlier_with_docs["documents"] = docs
                outliers_with_docs.append(outlier_with_docs)
            
            # Only add to results if there are filtered outliers remaining
            if outliers_with_docs:
                results.append({
                    "event": event,
                    "outliers": outliers_with_docs,
                    "total_times": len(times)
                })
    
    return results

def process_all_swimmers_outliers(collection, output_dir="outliers", method='iqr', factor=1.5, season="2025-2026"):
    """
    Process swimmers who have data in the specified season, find their outliers (from all years), and write results to files.
    
    Args:
        collection: MongoDB collection object
        output_dir: Directory to save output files (default "outliers")
        method: Method to use for outlier detection ('iqr' or 'zscore')
        factor: Multiplier for IQR method (default 1.5)
        season: Season to filter swimmers by (default "2025-2026"). Only swimmers with data in this season are processed.
    
    Returns:
        Dict with swimmer names as keys and number of events with outliers as values
    """
    # Get all unique swimmers who have data in the specified season (nj.com only)
    swimmers_in_season = collection.distinct("swimmer", {"source": "njcom", "year": season})
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    results_summary = {}
    
    print(f"Processing {len(swimmers_in_season)} swimmers with data in {season} season...")
    print("(Outliers may come from any year)\n")
    
    for swimmer in swimmers_in_season:
        # Find outliers for this swimmer
        outliers = find_all_outliers_for_swimmer(collection, swimmer, method=method, factor=factor)
        
        # Only write file if there are outliers
        if outliers:
            # Create safe filename
            safe_name = swimmer.replace(' ', '_').replace('/', '_')
            filename = os.path.join(output_dir, f"{safe_name}_outliers.json")
            
            # Write to JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "swimmer": swimmer,
                    "outliers": outliers
                }, f, indent=2, ensure_ascii=False)
            
            num_events = len(outliers)
            results_summary[swimmer] = num_events
            print(f"  ✓ {swimmer}: {num_events} event(s) with outliers")
    
    print(f"\n✓ Complete! Processed {len(swimmers_in_season)} swimmers, found outliers for {len(results_summary)} swimmers")
    return results_summary

def fix_specific_location(collection, old_location, new_location=None, new_course="SCY", exact_match=True):
    """
    Fix a specific location string by rewriting it and updating the course.
    
    Args:
        collection: MongoDB collection object
        old_location: The location string to find (or prefix if exact_match=False)
        new_location: The new location string to write (if None, location is not changed)
        new_course: The course to set (default "SCY")
        exact_match: If True, match location exactly. If False, match if location starts with old_location
    
    Returns:
        Number of times updated
    """
    # Find all nj.com documents
    njcom_docs = list(collection.find({"source": "njcom"}))
    
    updated_count = 0
    fixed_times = 0
    
    for doc in njcom_docs:
        data = doc.get('data', [])
        if not data:
            continue
        
        doc_updated = False
        
        # Check each event's times
        for event_data in data:
            times = event_data.get('times', [])
            for time_entry in times:
                location = time_entry.get('location', '')
                
                # Check if location matches
                if exact_match:
                    matches = (location == old_location)
                else:
                    matches = location.startswith(old_location)
                
                if matches:
                    # Update location if new_location is provided
                    if new_location is not None:
                        time_entry['location'] = new_location
                    # Update course
                    time_entry['course'] = new_course
                    doc_updated = True
                    fixed_times += 1
        
        # Update the document if any times were fixed
        if doc_updated:
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"data": data}}
            )
            updated_count += 1
    
    print(f"Fixed {fixed_times} times across {updated_count} documents")
    return fixed_times

def load_impossible_times(filename="impossibletimes.json"):
    """Load impossible time thresholds from JSON file"""
    file_path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filename} not found.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error reading {filename}: {e}")
        return {}

def find_and_handle_impossible_times(collection, impossible_times_file="impossibletimes.json", flag_file="impossible_times_flagged.txt"):
    """
    Find impossible times (faster than thresholds) and prompt user for action.
    
    Args:
        collection: MongoDB collection object
        impossible_times_file: Path to JSON file with impossible time thresholds
        flag_file: File to write flagged swimmers to
    """
    # Load impossible times
    impossible_data = load_impossible_times(impossible_times_file)
    if not impossible_data:
        print("No impossible times data loaded. Exiting.")
        return
    
    # Get gender-specific thresholds (assuming we're checking female times for now)
    thresholds = impossible_data.get("female", {})
    if not thresholds:
        print("No female thresholds found in impossible times file.")
        return
    
    print(f"Loaded thresholds for {len(thresholds)} events")
    print("Finding impossible times in nj.com documents...\n")
    
    # Get all nj.com documents
    njcom_docs = list(collection.find({"source": "njcom"}))
    
    impossible_times_found = []
    
    # Process each document
    for doc in njcom_docs:
        swimmer = doc.get("swimmer", "")
        year = doc.get("year", "")
        data = doc.get('data', [])
        
        if not data:
            continue
        
        # Check each event
        for event_data in data:
            event_name = event_data.get('event', '')
            
            # Skip if event not in thresholds
            if event_name not in thresholds:
                continue
            
            threshold_seconds = thresholds[event_name]
            times = event_data.get('times', [])
            
            # Check each time
            for time_entry in times:
                time_str = time_entry.get('time', '')
                if not time_str:
                    continue
                
                # Parse time to seconds
                time_seconds = parse_time_to_seconds(time_str)
                if time_seconds is None:
                    continue
                
                # Get course and convert to SCY
                course = time_entry.get('course', 'SCY')
                time_scy = convert_time_to_scy(time_seconds, event_name, course)
                
                if time_scy is None:
                    continue
                
                # Check if time is faster than impossible threshold
                if time_scy < threshold_seconds:
                    location = time_entry.get('location', '')
                    impossible_times_found.append({
                        'swimmer': swimmer,
                        'year': year,
                        'event': event_name,
                        'time': time_str,
                        'time_scy': time_scy,
                        'threshold': threshold_seconds,
                        'location': location,
                        'doc_id': doc['_id'],
                        'event_data': event_data,
                        'time_entry': time_entry
                    })
    
    print(f"Found {len(impossible_times_found)} impossible time(s)\n")
    
    if not impossible_times_found:
        print("No impossible times found!")
        return
    
    # Process each impossible time
    for i, item in enumerate(impossible_times_found, 1):
        swimmer = item['swimmer']
        year = item['year']
        event = item['event']
        time_str = item['time']
        time_scy = item['time_scy']
        threshold = item['threshold']
        location = item['location']
        
        print(f"\n[{i}/{len(impossible_times_found)}] IMPOSSIBLE TIME FOUND:")
        print(f"  Swimmer: {swimmer}")
        print(f"  Year: {year}")
        print(f"  Event: {event}")
        print(f"  Time: {time_str} (SCY: {time_scy:.2f}s)")
        print(f"  Threshold: {threshold:.2f}s")
        print(f"  Location: {location}")
        
        while True:
            action = input("\nAction: [d]elete, [f]lag, [p]ass, [q]uit all: ").strip().lower()
            
            if action == 'd':
                # Delete the time
                doc_id = item['doc_id']
                target_time = item['time']
                target_location = item['location']
                
                # Get the document and update it
                doc = collection.find_one({"_id": doc_id})
                if doc:
                    data = doc.get('data', [])
                    # Find the event and remove the time entry
                    for ed in data:
                        if ed.get('event') == event:
                            times = ed.get('times', [])
                            # Remove the matching time entry (match by time and location)
                            times = [t for t in times if not (t.get('time') == target_time and t.get('location') == target_location)]
                            ed['times'] = times
                            break
                    
                    collection.update_one(
                        {"_id": doc_id},
                        {"$set": {"data": data}}
                    )
                    print(f"  ✓ Deleted time for {swimmer}")
                break
                
            elif action == 'f':
                # Flag the swimmer (write to file)
                with open(flag_file, 'a', encoding='utf-8') as f:
                    f.write(f"{swimmer}|{year}|{event}|{time_str}|{time_scy:.2f}|{threshold:.2f}|{location}\n")
                print(f"  ✓ Flagged {swimmer} - written to {flag_file}")
                break
                
            elif action == 'p':
                # Pass - do nothing
                print(f"  ○ Passed - no action taken")
                break
                
            elif action == 'q':
                # Quit all
                print("  Exiting...")
                return
                
            else:
                print("  Invalid choice. Please enter 'd', 'f', 'p', or 'q'")
    
    print(f"\n✓ Processed {len(impossible_times_found)} impossible time(s)")




