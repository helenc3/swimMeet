from common.utils import OFFICIAL_COLLECTION_NAME
from common.utils import PENALTY_FACTOR, EVENT_MAP, EVENT_MAP_EQUIVALENTS


"""
query functions for the newer collection, OFFICIAL_COLLECTION_NAME
"""


######## waitt ok gonna leave it att this for the moment...
### to be updated for convenience. 
def query_team_swimmers(db, season, team):
    """
    Args: db, 
          year: Season year (e.g., "2024-2025") string
          team: Team name (e.g., "Princeton") string
    Returns: List of swimmers name strings in the team for the given year

    """
    collection = db[OFFICIAL_COLLECTION_NAME]
    query = {
        f"teams.{season}": team
    }
    swimmers = collection.find(query)
    list_of_swimmers = []
    for swimmer in swimmers:
        list_of_swimmers.append(swimmer["swimmer"])
    return list_of_swimmers

def get_best_times(db, swimmer_name, penalty_factor = PENALTY_FACTOR):
    """
    Args: db, 
          swimmer_name: Swimmer name (e.g., "John Doe") string
    Returns: dict, besttimes[event] = time
    if best time for event is null, looks in predicted times and returns the predicted time * penalty factor
    """
    collection = db[OFFICIAL_COLLECTION_NAME]
    query = {
        "swimmer": swimmer_name
    }
    swimmer = collection.find_one(query)
    bestimes = swimmer["best_times"]
    for event in bestimes:
        if bestimes[event] is None:
            try:
                bestimes[event] = swimmer["predicted_times"][event]["time"] * penalty_factor
            except:
                print(f"No predicted time for {event} for {swimmer_name}")
                bestimes[event] = None
    return bestimes

def get_times_matrix(db, season, team, event_map = EVENT_MAP, event_map_equivalents = EVENT_MAP_EQUIVALENTS):
    """
    Args: db, 
          year: Season year (e.g., "2024-2025") string
          team: Team name (e.g., "Princeton") string
          event_map: dict, event_map[index] = event name
          event_map_equivalents: dict, event_map_equivalents[relay event] = individual event name
    Returns: list of swimmers, 2d array times[swimmer][event] = besttime
    """
    swimmers = query_team_swimmers(db, season, team)
    times_matrix = []
    for swimmer in swimmers:
        bestimes = get_best_times(db, swimmer)
        swimmer_times = []
        for event_idx in event_map:
            event_name = event_map[event_idx]
            if event_name in event_map_equivalents:
                event_name = event_map_equivalents[event_name]
            time = bestimes[event_name]
            swimmer_times.append(time)
        times_matrix.append(swimmer_times)
    return swimmers, times_matrix
    