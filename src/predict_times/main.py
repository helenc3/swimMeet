from common.mongodb.connect import connect_to_mongodb
from common.utils import OFFICIAL_COLLECTION_NAME
from predict_times.utils import predict_missing_times
    


"""
main file to predict missing times for all swimmers in the database -- run this one
"""


mongo_client, db = connect_to_mongodb()
collection = db[OFFICIAL_COLLECTION_NAME]

swimmers = collection.distinct("swimmer")

for swimmer in swimmers:
    swimmer_doc = collection.find_one({"swimmer": swimmer})
    if swimmer_doc and "best_times" in swimmer_doc:
        best_times = swimmer_doc["best_times"]
            
        # extract just the time values (handle dict structures if they exist)
        best_times_for_prediction = {}
        for event, value in best_times.items():
            if isinstance(value, dict):
                # If already a dict, use the time field (could be None or a number)
                best_times_for_prediction[event] = value.get("time")
            else:
                # If it's just a number or None, use it directly
                best_times_for_prediction[event] = value
        
        # Check if all best times are None
        all_null = all(time is None for time in best_times_for_prediction.values())
        inputted_50_free = None
        
        if all_null:
            # Ask user for 50 Free time
            while True:
                try:
                    user_input = input(f"All best times are null for {swimmer}. Please enter a 50 Free time in seconds (e.g., 25.5): ")
                    inputted_50_free = float(user_input)
                    if inputted_50_free > 0:
                        # Add the inputted 50 Free to best_times_for_prediction
                        best_times_for_prediction["50 Free"] = inputted_50_free
                        print(f"Using 50 Free time: {inputted_50_free} seconds for {swimmer}")
                        break
                    else:
                        print("Time must be positive. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        
        # Check if there are any missing times to predict
        missing_events = [event for event, time in best_times_for_prediction.items() if time is None]
        if missing_events:
            try:
                predictions = predict_missing_times(best_times_for_prediction)
                
                # Prepare predicted_times dict with nested structure: {event: {time: X, confidence: Y}}
                predicted_times = {}
                for event, (predicted_time, confidence) in predictions.items():
                    predicted_times[event] = {
                        "time": predicted_time,
                        "confidence": confidence
                    }
                
                # If we inputted a 50 Free time, add it to predicted_times as well
                if inputted_50_free is not None:
                    predicted_times["50 Free"] = {
                        "time": inputted_50_free,
                        "confidence": 3  # High confidence since it was user-provided
                    }
                
                # Update the document with predicted_times field (separate from best_times)
                # This replaces the entire predicted_times field with new predictions
                collection.update_one(
                    {"swimmer": swimmer},
                    {"$set": {"predicted_times": predicted_times}}
                )
                
                print(f"Added predicted times for {swimmer}: {list(predicted_times.keys())}")
            except Exception as e:
                print(f"Error predicting times for {swimmer}: {e}")