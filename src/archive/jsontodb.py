import json
from pathlib import Path
from common.mongodb.connect import connect_to_mongodb
from common.utils import COLLECTION_NAME, NJCOM_DATA_DIR

## note: this is script is almost fully ai generated code. use with caution.
## hopefully i never have to run this again. :pray:
    
def migrate_json_files_to_mongodb(db):
    """
    migrate all existing JSON files from data/njcom/ to MongoDB
    this is a one-time migration script
    ive already run this- so plz only call this method in an absolute emergency
    warning: this will overwrite existing data in the database
    """

    collection = db[COLLECTION_NAME]
    
    data_dir = Path(NJCOM_DATA_DIR)
    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist!")
        return
    
    migrated_count = 0
    
    # Walk through all year directories
    for year_dir in data_dir.iterdir():
        if not year_dir.is_dir() or not any(char.isdigit() for char in year_dir.name):
            continue
        
        year = year_dir.name
        print(f"\nProcessing year: {year}")
        
        # Walk through all team directories
        for team_dir in year_dir.iterdir():
            if not team_dir.is_dir():
                continue
            
            team = team_dir.name
            swimmers_dir = team_dir / "swimmers"
            
            if not swimmers_dir.exists():
                continue
            
            # Process all JSON files in swimmers directory
            for json_file in swimmers_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        swimmer_data = json.load(f)
                    
                    # Add metadata (year, team, source) - keep nested structure
                    swimmer_data['year'] = year
                    swimmer_data['team'] = team
                    swimmer_data['source'] = 'njcom'
                    
                    # Insert or update in MongoDB
                    # Using swimmer name + year + team + source as unique identifier
                    result = collection.update_one(
                        {
                            'swimmer': swimmer_data['swimmer'],
                            'year': year,
                            'team': team,
                            'source': 'njcom'
                        },
                        {'$set': swimmer_data},
                        upsert=True  # Create if doesn't exist
                    )
                    
                    if result.upserted_id:
                        print(f"  ✓ Inserted: {swimmer_data['swimmer']} ({team})")
                    else:
                        print(f"  ✓ Updated: {swimmer_data['swimmer']} ({team})")
                    
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"  ✗ Error processing {json_file}: {e}")
    
    print(f"\n✓ Migration complete! Migrated {migrated_count} swimmer records.")