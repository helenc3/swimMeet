##this is just a one time test script

from mongodb_helper import connect_to_mongodb
import re




def parse_teams_from_location(location_str):
    """
    Parses the team after "at" from a location string in format:
    "12/16/2025, Hopewell Valley (97) at Hightstown (73)"
    
    Returns:
        str: team name after "at" or None if parsing fails
    """
    if not location_str:
        print(f"No location string found for {location_str}")
        return None
    
    # Pattern: date, team1 (score) at team2 (score)
    # Match: team name after " at ", then (score)
    pattern = r'at\s+([^(]+?)\s*\([^)]+\)'
    match = re.search(pattern, location_str)
    
    if match:
        team = match.group(1).strip()
        return team
    
    print(f"No match found for {location_str}")
    return None


def get_unique_teams_for_swimmer(swimmer_name, collection):
    """
    Gets all unique teams found in location strings for a swimmer's njcom data
    Returns a set of team names
    """
    swimmer_docs = list(collection.find({"swimmer": swimmer_name, "source": "njcom"}))
    
    unique_teams = set()
    
    for doc in swimmer_docs:
        data = doc.get('data', [])
        for event_data in data:
            times = event_data.get('times', [])
            for time_entry in times:
                location = time_entry.get('location', '')
                if location:
                    team = parse_teams_from_location(location)
                    if team:
                        unique_teams.add(team)
    
    return unique_teams


def print_unique_teams_for_all_swimmers(collection, filename="all_unique_teams.txt"):
    """
    Prints all unique teams found across ALL swimmers (no duplicates)
    If a team appears in multiple swimmers' data, it's only listed once
    Also saves the output to a file
    """
    unique_swimmers = collection.distinct("swimmer", {"source": "njcom"})
    
    all_unique_teams = set()
    
    for swimmer_name in sorted(unique_swimmers):
        swimmer_teams = get_unique_teams_for_swimmer(swimmer_name, collection)
        all_unique_teams.update(swimmer_teams)
    
    # Print to console
    print("\nAll unique teams found across all swimmers:")
    for team in sorted(all_unique_teams):
        print(f"  - {team}")
    
    print(f"\nTotal: {len(all_unique_teams)} unique teams")
    
    # Save to file
    with open(filename, "w", encoding="utf-8") as f:
        f.write("All unique teams found across all swimmers:\n")
        for team in sorted(all_unique_teams):
            f.write(f"{team}\n")

    
    print(f"✓ Saved output to {filename}")


def save_unique_teams_per_swimmer_to_file(collection, filename="swimmer_teams.txt"):
    """
    Gets unique teams for every swimmer and saves them to a text file
    Each swimmer's teams are listed separately
    """
    unique_swimmers = collection.distinct("swimmer", {"source": "njcom"})
    
    with open(filename, "w", encoding="utf-8") as f:
        for swimmer_name in sorted(unique_swimmers):
            swimmer_teams = get_unique_teams_for_swimmer(swimmer_name, collection)
            
            if swimmer_teams:
                f.write(f"{swimmer_name}:\n")
                for team in sorted(swimmer_teams):
                    f.write(f"  - {team}\n")
                f.write("\n")
            else:
                f.write(f"{swimmer_name}: No teams found\n\n")
    
    print(f"✓ Saved unique teams for all swimmers to {filename}")


def find_swimmers_and_times_by_team(collection):
    """
    Interactive function that:
    1. Asks for a team name
    2. Prints all swimmers that have that team in their unique team list
    3. Prompts user to choose a swimmer
    4. Prints times swum 'at' that team, and all other times in those same events
    5. Allows changing teams or selecting multiple swimmers
    """
    # Outer loop to allow changing teams
    while True:
        # Step 1: Ask for team name
        team_name = input("\nEnter team name to search for (or 'q' to quit): ").strip()
        if not team_name or team_name.lower() == 'q':
            print("Exiting.")
            return
        
        # Step 2: Find all swimmers that have this team in their unique teams
        unique_swimmers = collection.distinct("swimmer", {"source": "njcom"})
        swimmers_with_team = []
        
        for swimmer_name in sorted(unique_swimmers):
            swimmer_teams = get_unique_teams_for_swimmer(swimmer_name, collection)
            if team_name in swimmer_teams:
                swimmers_with_team.append(swimmer_name)
        
        if not swimmers_with_team:
            print(f"\nNo swimmers found with team '{team_name}' in their data.")
            continue  # Go back to team selection
        
        # Step 3: Loop to allow selecting multiple swimmers
        while True:
            # Display swimmers and prompt for selection
            print(f"\nSwimmers with team '{team_name}' in their data:")
            for idx, swimmer in enumerate(swimmers_with_team, 1):
                print(f"  {idx}. {swimmer}")
            
            selected_swimmer = None
            while True:
                try:
                    choice = input(f"\nSelect a swimmer (1-{len(swimmers_with_team)}), 't' for new team, or 'q' to quit: ").strip()
                    if choice.lower() == 'q':
                        print("Exiting.")
                        return
                    if choice.lower() == 't':
                        break  # Break out of swimmer selection loop to go back to team selection
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(swimmers_with_team):
                        selected_swimmer = swimmers_with_team[choice_num - 1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(swimmers_with_team)}, 't' for new team, or 'q' to quit")
                except ValueError:
                    print("Please enter a valid number, 't' for new team, or 'q' to quit")
            
            # If user chose 't', break out of swimmer loop to go back to team selection
            if choice.lower() == 't':
                break
            
            # If no swimmer selected, continue to next iteration
            if selected_swimmer is None:
                continue
            
            # Step 4: Find times 'at' the team and all other times in those events
            swimmer_docs = list(collection.find({"swimmer": selected_swimmer, "source": "njcom"}))
            
            # First, collect all times 'at' the team and their events
            times_at_team = []  # List of (event, time_entry) tuples
            events_at_team = set()  # Set of events that have times 'at' the team
            
            for doc in swimmer_docs:
                data = doc.get('data', [])
                for event_data in data:
                    event = event_data.get('event', '')
                    times = event_data.get('times', [])
                    for time_entry in times:
                        location = time_entry.get('location', '')
                        if location:
                            parsed_team = parse_teams_from_location(location)
                            if parsed_team == team_name:
                                times_at_team.append((event, time_entry))
                                events_at_team.add(event)
            
            if not times_at_team:
                print(f"\nNo times found for {selected_swimmer} 'at' {team_name}.")
            else:
                # Print times 'at' the team
                print(f"\n{'='*60}")
                print(f"Times for {selected_swimmer} 'at' {team_name}:")
                print(f"{'='*60}")
                
                # Group by event
                times_by_event = {}
                for event, time_entry in times_at_team:
                    if event not in times_by_event:
                        times_by_event[event] = []
                    times_by_event[event].append(time_entry)
                
                for event in sorted(times_by_event.keys()):
                    print(f"\n{event}:")
                    for time_entry in sorted(times_by_event[event], key=lambda x: x.get('date', '')):
                        time_str = time_entry.get('time', 'N/A')
                        date_str = time_entry.get('date', 'N/A')
                        location_str = time_entry.get('location', 'N/A')
                        print(f"  Time: {time_str} | Date: {date_str} | Location: {location_str}")
                
                # Now find all other times in those same events (from all locations)
                print(f"\n{'='*60}")
                print(f"All other times for {selected_swimmer} in these events:")
                print(f"{'='*60}")
                
                for doc in swimmer_docs:
                    data = doc.get('data', [])
                    for event_data in data:
                        event = event_data.get('event', '')
                        if event in events_at_team:  # Only show times for events that have 'at' team times
                            times = event_data.get('times', [])
                            other_times = []
                            for time_entry in times:
                                location = time_entry.get('location', '')
                                if location:
                                    parsed_team = parse_teams_from_location(location)
                                    # Include times that are NOT 'at' the specified team
                                    if parsed_team != team_name:
                                        other_times.append(time_entry)
                                else:
                                    # If no location or can't parse, include it as "other"
                                    other_times.append(time_entry)
                            
                            if other_times:
                                print(f"\n{event}:")
                                for time_entry in sorted(other_times, key=lambda x: x.get('date', '')):
                                    time_str = time_entry.get('time', 'N/A')
                                    date_str = time_entry.get('date', 'N/A')
                                    location_str = time_entry.get('location', 'N/A')
                                    print(f"  Time: {time_str} | Date: {date_str} | Location: {location_str}")
            
            # Loop back to show swimmer list again (user can type 'q' to quit when selecting)


client, db = connect_to_mongodb()
if db is None:
    print("Failed to connect to MongoDB. Exiting.")
    exit(1)

collection = db["swimmers"]

#print_unique_teams_for_all_swimmers(collection)
#save_unique_teams_per_swimmer_to_file(collection)
find_swimmers_and_times_by_team(collection)
