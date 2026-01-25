"""
Fix course errors for nj.com documents where location contains "at Robbinsville".
The course should reflect the OTHER team's course (the team before "at"), not Robbinsville's course.
"""

from mongodb_helper import connect_to_mongodb, COLLECTION_NAME
import re
import json
import os

def parse_team_before_at(location_str):
    """
    Parses the team BEFORE "at" from a location string in format:
    "12/16/2025, Hopewell Valley (97) at Hightstown (73)"
    
    Returns:
        str: team name before "at" or None if parsing fails
    """
    if not location_str:
        return None
    
    # Pattern: date, team1 (score) at team2 (score)
    # Match: team name before " at ", then (score)
    pattern = r',\s*([^(]+?)\s*\([^)]+\)\s+at\s+'
    match = re.search(pattern, location_str)
    
    if match:
        team = match.group(1).strip()
        return team
    
    return None

def load_team_courses(teamcourses_file='teamcourses.json'):
    """Load team courses from JSON file"""
    file_path = os.path.join(os.path.dirname(__file__), teamcourses_file)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {teamcourses_file} not found.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error reading {teamcourses_file}: {e}")
        return {}

def fix_robbinsville_courses(collection, team_courses, year_specific_overrides=None):
    """
    Fix course fields for all nj.com documents where location contains "at Robbinsville".
    
    Args:
        collection: MongoDB collection object
        team_courses: Dict mapping team names to courses
        year_specific_overrides: Dict of {year: {team: course}} for year-specific overrides
    """
    if year_specific_overrides is None:
        year_specific_overrides = {}
    
    # Find all nj.com documents
    njcom_docs = list(collection.find({"source": "njcom"}))
    
    updated_count = 0
    fixed_times = 0
    
    for doc in njcom_docs:
        data = doc.get('data', [])
        if not data:
            continue
        
        doc_updated = False
        year = doc.get('year')
        
        # Check each event's times
        for event_data in data:
            times = event_data.get('times', [])
            for time_entry in times:
                location = time_entry.get('location', '')
                
                # Check if location contains "at Robbinsville" (case insensitive)
                if location and 'at robbinsville' in location.lower():
                    # Parse the team before "at"
                    other_team = parse_team_before_at(location)
                    
                    if other_team:
                        # Determine course for this team
                        course = None
                        
                        # Check year-specific overrides first
                        if year in year_specific_overrides:
                            if other_team in year_specific_overrides[year]:
                                course = year_specific_overrides[year][other_team]
                        
                        # If no override, check team_courses
                        if course is None:
                            course = team_courses.get(other_team, 'SCY')  # Default to SCY if not found
                        
                        # Update the course field
                        time_entry['course'] = course
                        doc_updated = True
                        fixed_times += 1
        
        # Update the document if any times were fixed
        if doc_updated:
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"data": data}}
            )
            updated_count += 1
    
    print(f"Fixed courses for {fixed_times} times across {updated_count} documents")
    return updated_count, fixed_times

if __name__ == "__main__":
    client, db = connect_to_mongodb()
    if db is None:
        print("Failed to connect to MongoDB. Exiting.")
        exit(1)
    
    collection = db[COLLECTION_NAME]
    
    # Load team courses
    team_courses = load_team_courses()
    
    # Year-specific overrides (if any)
    year_specific_overrides = {
        "2022-2023": {
            "West Windsor-Plainsboro South": "SCM"
        }
    }
    
    print("Fixing course errors for locations containing 'at Robbinsville'...")
    updated_count, fixed_times = fix_robbinsville_courses(collection, team_courses, year_specific_overrides)
    print(f"\n✓ Complete! Updated {updated_count} documents, fixed {fixed_times} times")
