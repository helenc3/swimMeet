"""
MongoDB Helper Script for Swim Meet Data

First, install pymongo:
  conda activate py312
  pip install pymongo

Or if you're using MongoDB Atlas (cloud):
  pip install pymongo[srv]

Then update the connection string below with your MongoDB connection string.
"""

from pymongo import MongoClient
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Your MongoDB connection string (loaded from .env file)
# Create a .env file with: MONGODB_URI=your_connection_string_here
# See .env.example for template
MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError(
        "MONGODB_URI not found in environment variables. "
        "Please create a .env file with your MongoDB connection string. "
        "See .env.example for template."
    )

# Database and collection names
DB_NAME = "swimmeet"
COLLECTION_NAME = "swimmers"

def connect_to_mongodb():
    """Connect to MongoDB and return the database"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        print(f"Connected to MongoDB! Database: {DB_NAME}")
        return client, db
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        print("\nMake sure you:")
        print("1. Have installed pymongo: pip install pymongo")
        print("2. Have the correct connection string")
        print("3. Are connected to the internet (if using Atlas)")
        return None, None

# def migrate_json_files_to_mongodb(db):

#     ## ive already run these- so plz only call this method in an emergency
#     ## actually i will comment this out for now
#     """
#     Migrate all existing JSON files from data/njcom/ to MongoDB
#     This is a one-time migration script
#     """
#     collection = db[COLLECTION_NAME]
    
#     data_dir = Path("data/njcom")
#     if not data_dir.exists():
#         print(f"Error: {data_dir} does not exist!")
#         return
    
#     migrated_count = 0
    
#     # Walk through all year directories
#     for year_dir in data_dir.iterdir():
#         if not year_dir.is_dir() or not any(char.isdigit() for char in year_dir.name):
#             continue
        
#         year = year_dir.name
#         print(f"\nProcessing year: {year}")
        
#         # Walk through all team directories
#         for team_dir in year_dir.iterdir():
#             if not team_dir.is_dir():
#                 continue
            
#             team = team_dir.name
#             swimmers_dir = team_dir / "swimmers"
            
#             if not swimmers_dir.exists():
#                 continue
            
#             # Process all JSON files in swimmers directory
#             for json_file in swimmers_dir.glob("*.json"):
#                 try:
#                     with open(json_file, 'r', encoding='utf-8') as f:
#                         swimmer_data = json.load(f)
                    
#                     # Add metadata (year, team, source) - keep nested structure
#                     swimmer_data['year'] = year
#                     swimmer_data['team'] = team
#                     swimmer_data['source'] = 'njcom'
                    
#                     # Insert or update in MongoDB
#                     # Using swimmer name + year + team + source as unique identifier
#                     result = collection.update_one(
#                         {
#                             'swimmer': swimmer_data['swimmer'],
#                             'year': year,
#                             'team': team,
#                             'source': 'njcom'
#                         },
#                         {'$set': swimmer_data},
#                         upsert=True  # Create if doesn't exist
#                     )
                    
#                     if result.upserted_id:
#                         print(f"  ✓ Inserted: {swimmer_data['swimmer']} ({team})")
#                     else:
#                         print(f"  ✓ Updated: {swimmer_data['swimmer']} ({team})")
                    
#                     migrated_count += 1
                    
#                 except Exception as e:
#                     print(f"  ✗ Error processing {json_file}: {e}")
    
#     print(f"\n✓ Migration complete! Migrated {migrated_count} swimmer records.")

def get_swimmer_event_times(db, swimmer_name, event_name, year=None, team=None, source=None):
    """
    Get all times for a specific event for a swimmer
    Example: get_swimmer_event_times(db, "John Doe", "100 Fly", year="2024-2025")
    """

    ## this will have to be updated when swimcloud data comes in
    collection = db[COLLECTION_NAME]
    
    query = {
        "swimmer": swimmer_name,
        "data.event": event_name  # Query nested array
    }
    if year:
        query["year"] = year
    if team:
        query["team"] = team
    if source:
        query["source"] = source
    
    swimmer = collection.find_one(query)
    
    if not swimmer:
        return []
    
    # Extract just the times for the specific event from nested data array
    event_data = [event for event in swimmer.get('data', []) if event.get('event') == event_name]
    
    if event_data:
        return event_data[0].get('times', [])
    return []

def get_all_swimmers_with_event(db, event_name, year=None, team=None, source=None):
    """
    Get all swimmers who have times for a specific event
    Example: get_all_swimmers_with_event(db, "100 Fly", year="2024-2025")
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

def example_queries(db):
    """Example queries you can run on your MongoDB data"""
    ## this isnt a tool just an example
    collection = db[COLLECTION_NAME]
    
    print("\n" + "="*50)
    print("EXAMPLE QUERIES:")
    print("="*50)
    
    # Example 1: Find all swimmers from Princeton in 2024-2025
    print("\n1. Find all swimmers from Princeton in 2024-2025:")
    princeton_swimmers = collection.find({"team": "Princeton", "year": "2024-2025"})
    for swimmer in princeton_swimmers:
        print(f"   - {swimmer['swimmer']}")
    
    # Example 2: Get 100 Fly times for a specific swimmer
    print("\n2. Get 100 Fly times for a swimmer:")
    fly_times = get_swimmer_event_times(db, "John Doe", "100 Fly", year="2024-2025")
    print(f"   Found {len(fly_times)} times")
    print("   Using helper: get_swimmer_event_times(db, 'John Doe', '100 Fly', year='2024-2025')")
    
    # Example 3: Get all swimmers with 100 Fly times
    print("\n3. All swimmers with 100 Fly times in 2024-2025:")
    swimmers_with_fly = get_all_swimmers_with_event(db, "100 Fly", year="2024-2025")
    print(f"   Found {len(swimmers_with_fly)} swimmers")
    
    # Example 4: Count total swimmers
    print(f"\n4. Total swimmers in database: {collection.count_documents({})}")
    
    # Example 5: Get all teams
    print("\n5. All teams in database:")
    teams = collection.distinct("team")
    for team in sorted(teams):
        print(f"   - {team}")

def save_swimmer_to_mongodb(db, swimmer_data, year=None, team=None, profile=None, source='njcom'):
    """
    Save a single swimmer's data to MongoDB
    Merges new times with existing data, avoiding duplicates
    
    Args:
        db: MongoDB database object
        swimmer_data: Dictionary with 'swimmer' and 'data' keys
            - For njcom: 'data' is list of events with times (from scrapeDataForOneSwimmer)
            - For swimcloud: 'data' is flat list of dicts with 'event', 'course', 'time' (from scrapeprofile)
        year: Season year (e.g., "2024-2025") - required for njcom
        team: Team name - required for njcom
        profile: Profile name (e.g., "Helen Chen WWP South") - required for swimcloud
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
            # Note: swimcloud doesn't have location, so we don't include it
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


