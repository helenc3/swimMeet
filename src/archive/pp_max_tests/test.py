import sys
from pathlib import Path
from lineup.model_utils import make_lineup, add_constraints, maximize_powerpoints
from common.utils import EVENT_MAP, INDIV_EVENT_COUNT, MR_EVENT_START_IDX, MR_POSITION_COUNT, RELAY_COUNT, TOTAL_EVENT_COUNT, FR2_START_IDX, FR4_START_IDX, FR_RELAY_COUNT
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.mongodb.connect import connect_to_mongodb
from common.mongodb.queries2 import get_times_matrix
from common.utils import OFFICIAL_COLLECTION_NAME
from ortools.sat.python import cp_model

"""
this script tests the powerpoint maximization system
it will output the lineup with the highest powerpoints, writes to csv file
"""

output_file = "lineup/max_powerpoint_lineup.csv"
season = '2025-2026'
team = "Princeton"
gender = "female"


client, db = connect_to_mongodb()
if db is None:
    print("Failed to connect to MongoDB. Exiting.")
    exit(1)

swimmers, times = get_times_matrix(db, season, team)
model = cp_model.CpModel()

lineup = make_lineup(model, swimmers)
add_constraints(model, lineup, swimmers, times) ## adds constraints to the model
maximize_powerpoints(model, lineup, swimmers, times, gender) ## adds the objective function to the model

solver = cp_model.CpSolver()
status = solver.Solve(model)

with open(output_file, "w") as f:
    f.write(f"status: {solver.StatusName(status)}\n")
    f.write(f"Total PP: {solver.ObjectiveValue()}\n")
    f.write("Event,Swimmer\n")
    for e in range(TOTAL_EVENT_COUNT):
        swimmers_in_event = [swimmers[s] for s in range(len(swimmers)) if solver.Value(lineup[s][e]) == 1]
        if swimmers_in_event:
            f.write(f"{EVENT_MAP[e]},{', '.join(swimmers_in_event)}\n")