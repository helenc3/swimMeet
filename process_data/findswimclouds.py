"""
Script to find swimmers with no swimcloud documents in the swimmers collection
"""

from mongodb_helper import connect_to_mongodb, COLLECTION_NAME
import json

def find_swimmers_without_swimcloud(collection=None, season="2025-2026"):
    """
    Find all swimmers in the collection that have no swimcloud documents,
    but only for swimmers who have non-empty 2025-2026 season documents.
    
    Args:
        collection: MongoDB collection object. If None, will connect automatically.
        season: Season year to check (default: "2025-2026")
    
    Returns:
        List of swimmer names (strings) that have no swimcloud documents
    """
    if collection is None:
        client, db = connect_to_mongodb()
        collection = db[COLLECTION_NAME]
    
    # Get swimmers who have non-empty 2025-2026 nj.com documents
    swimmers_with_season_data = collection.distinct(
        "swimmer",
        {
            "source": "njcom",
            "year": season,
            "data": {"$exists": True, "$ne": [], "$not": {"$size": 0}}
        }
    )
    
    swimmers_without_swimcloud = []
    
    for swimmer in swimmers_with_season_data:
        # Check if this swimmer has any swimcloud documents
        swimcloud_docs = collection.find_one({
            "swimmer": swimmer,
            "source": "swimcloud"
        })
        
        if swimcloud_docs is None:
            swimmers_without_swimcloud.append(swimmer)
    
    return swimmers_without_swimcloud

if __name__ == "__main__":
    client, db = connect_to_mongodb()
    collection = db[COLLECTION_NAME]
    
    # Get swimmers with 2025-2026 data for stats
    swimmers_with_season_data = collection.distinct(
        "swimmer",
        {
            "source": "njcom",
            "year": "2025-2026",
            "data": {"$exists": True, "$ne": [], "$not": {"$size": 0}}
        }
    )
    
    print(f"Total swimmers with non-empty 2025-2026 data: {len(swimmers_with_season_data)}\n")
    print("Finding swimmers with no swimcloud documents...\n")
    
    swimmers_without_swimcloud = find_swimmers_without_swimcloud(collection)
    
    print(f"Swimmers without swimcloud documents: {len(swimmers_without_swimcloud)}\n")
    print("="*60)
    print("List of swimmers without swimcloud documents:")
    print("="*60)
    
    for swimmer in sorted(swimmers_without_swimcloud):
        print(swimmer)
    
    # Also save to a JSON file
    output_file = "swimmers_without_swimcloud.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(swimmers_without_swimcloud, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"List saved to: {output_file}")
    print(f"{'='*60}")
