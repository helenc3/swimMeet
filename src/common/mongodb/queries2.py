from common.utils import OFFICIAL_COLLECTION_NAME


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