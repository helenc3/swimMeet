from operator import not_
from scrapingUtilsv2 import ERRORS_PATH, save_meet_data_to_mongodb
from sconeswimmer import parse_time_to_seconds
from createswimmerprofsutils import convert_time_to_scy
from mongodb_helper import connect_to_mongodb
from createswimmerprofsutils import OFFICIAL_COLLECTION_NAME
import csv
import os

def readerrorfiles(ERRORS_PATH):
    data = []
    for file in os.listdir(ERRORS_PATH):
        if file.endswith(".csv"):
            if not file.endswith("_unverified.csv"):
                splitfile = file.split("_")
                event = splitfile[0] + " " + splitfile[1]
                course = splitfile[2]
                event_result = {
                    "event": event,
                    "course": "SCY",
                    "data": []
                    }
                with open(os.path.join(ERRORS_PATH, file), 'r') as f:
                    reader = csv.reader(f)
                    next(reader, None)  # Skip header row
                    for row in reader:
                        place = row[0]
                        name = row[1]
                        team = row[2]
                        time_str = row[3]
                        time_sec = parse_time_to_seconds(time_str)
                        if time_sec is None:
                            print(f"Warning: Could not parse time '{time_str}' for {name} in {event}")
                            continue
                        time_scy = convert_time_to_scy(time_sec, event, course)
                        if time_scy is None:
                            print(f"Warning: Could not convert time '{time_str}' for {name} in {event} {course}")
                            continue
                        event_result["data"].append({
                            "place": place,
                            "name": name,
                            "team": team,
                            "time": time_scy
                        })
                data.append(event_result)
    return data

def deleteerrorfiles(ERRORS_PATH):
    for file in os.listdir(ERRORS_PATH):
        if file.endswith(".csv"):
            if not file.endswith("_unverified.csv"):
                os.remove(os.path.join(ERRORS_PATH, file))
                print(f"Deleted {file}")

if __name__ == "__main__":
    client, db = connect_to_mongodb()
    collection = db[OFFICIAL_COLLECTION_NAME]
    data = readerrorfiles(ERRORS_PATH)
    
    if not data:
        print("No error event files found to process.")
    else:
        print(f"Processing {len(data)} event(s) from error files...")
        stats = save_meet_data_to_mongodb(data, collection)
        print(f"Meet stats: {stats}")
        deleteerrorfiles(ERRORS_PATH)
    
