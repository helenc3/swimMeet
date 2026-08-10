## script to get stats on the official swimmer profiles collection

from common.mongodb.connect import connect_to_mongodb
from collections import Counter
from common.utils import OFFICIAL_COLLECTION_NAME

"""
script to print swimmers with 8, 7, 6, or 5 null best times in the official swimmer profiles collection
might be useful to run once before predicting times if new data comes in
"""

client, db = connect_to_mongodb()
official_collection = db[OFFICIAL_COLLECTION_NAME]

# Get all swimmers
all_swimmers = list(official_collection.find({}))

total_swimmers = len(all_swimmers)
print(f"Total number of swimmers: {total_swimmers}\n")

# Count null times for each swimmer
null_counts = []
swimmers_by_null_count = {}  # Track swimmers by null count

for swimmer_doc in all_swimmers:
    swimmer_name = swimmer_doc.get("swimmer", "Unknown")
    best_times = swimmer_doc.get("best_times", {})
    if best_times is None:
        best_times = {}
    
    # Count how many None/null values are in best_times
    null_count = sum(1 for time in best_times.values() if time is None)
    null_counts.append(null_count)
    
    # Track swimmers by null count
    if null_count not in swimmers_by_null_count:
        swimmers_by_null_count[null_count] = []
    swimmers_by_null_count[null_count].append(swimmer_name)

# Count swimmers by number of null times
null_count_distribution = Counter(null_counts)

print("Number of swimmers by null times:")
print(f"  0 null times: {null_count_distribution.get(0, 0)}")
for i in range(1, max(null_counts) + 1 if null_counts else 1):
    count = null_count_distribution.get(i, 0)
    if count > 0:
        print(f"  {i} null time{'s' if i > 1 else ''}: {count}")

print(f"\nTotal: {sum(null_count_distribution.values())} swimmers")

# Print swimmers with 8, 7, 6, or 5 null times
print("\n" + "="*50)
print("Swimmers with 8, 7, 6, or 5 null times:")
print("="*50)

for null_count in [8, 7, 6, 5]:
    if null_count in swimmers_by_null_count:
        swimmers = swimmers_by_null_count[null_count]
        print(f"\n{null_count} null times ({len(swimmers)} swimmers):")
        for swimmer in sorted(swimmers):
            print(f"  - {swimmer}")
    else:
        print(f"\n{null_count} null times: 0 swimmers")
