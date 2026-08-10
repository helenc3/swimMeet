import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.mongodb.connect import connect_to_mongodb
from common.mongodb.queries2 import query_team_swimmers
from common.utils import OFFICIAL_COLLECTION_NAME
from ortools.sat.python import cp_model

EVENT_MAP = {
    0: '200 Free',
    1: '200 IM',
    2: '50 Free',
    3: '100 Fly',
    4: '100 Free',
    5: '500 Free',
    6: '100 Back',
    7: '100 Breast',
    8: '200 FR A',
    9: '200 FR B',
    10: '200 FR C',
    11: '400 FR A',
    12: '400 FR B',
    13: '400 FR C',
    14: '200 MR A1',
    15: '200 MR A2',
    16: '200 MR A3',
    17: '200 MR A4',
    18: '200 MR B1',
    19: '200 MR B2',
    20: '200 MR B3',
    21: '200 MR B4',
    22: '200 MR C1',
    23: '200 MR C2',
    24: '200 MR C3',
    25: '200 MR C4' }

INDIV_EVENT_COUNT = 8
MR_EVENT_START_IDX = 14 ## index of first MR event
MR_POSITION_COUNT = 4
MR_RELAY_COUNT = 3
TOTAL_EVENT_COUNT = 26

season = '2025-2026'
team = "West Windsor-Plainsboro South"


client, db = connect_to_mongodb()
if db is None:
    print("Failed to connect to MongoDB. Exiting.")
    exit(1)

swimmers = query_team_swimmers(db, season, team)
print(swimmers)

lineup = [] 
model = cp_model.CpModel()
for swimmer_idx in range(len(swimmers)):
    s_map = {'swimmer name': swimmers[swimmer_idx], 'swimmer idx': swimmer_idx, 'events': {}}
    e_map = {}
    for i in range(TOTAL_EVENT_COUNT): 
        e_map[i] = model.NewBoolVar(f"h_{swimmer_idx}_{i}")
    s_map['events'] = e_map
    lineup.append(s_map)


## constraints-- see planning doc for reference

## 1
for event_idx in range(INDIV_EVENT_COUNT): 
    event_lineup = []
    for swimmer in lineup:
        event_lineup.append(swimmer['events'][event_idx])
    model.add(sum(event_lineup) >= 1)
    model.add(sum(event_lineup) <= 3)

## 2 and 3
for swimmer in lineup:
    indiv_events = []
    total_events = []
    for event_idx in range(TOTAL_EVENT_COUNT):
        total_events.append(swimmer['events'][event_idx])
        if event_idx < INDIV_EVENT_COUNT:
            indiv_events.append(swimmer['events'][event_idx])

    model.add(sum(total_events) <= 4)
    model.add(sum(indiv_events) <= 2)

## 4a.
for event_idx in range(INDIV_EVENT_COUNT, MR_EVENT_START_IDX):  
    fr_event_lineup = []
    for swimmer in lineup:
        fr_event_lineup.append(swimmer['events'][event_idx])
    model.add_linear_expression_in_domain(sum(fr_event_lineup), 
    cp_model.Domain.from_values([0, 4]))


## todo: 5a, 5b
for swimmer in lineup:
    fr_relay = []
    mr_relay = []
    for event_idx in range(INDIV_EVENT_COUNT, MR_EVENT_START_IDX):
        fr_relay.append(swimmer['events'][event_idx])
    for event_idx in range(MR_EVENT_START_IDX, TOTAL_EVENT_COUNT):
        mr_relay.append(swimmer['events'][event_idx])
    model.add(sum(fr_relay) <= 1)
    model.add(sum(mr_relay) <= 1)


## 4b, 6
for relay in range(MR_RELAY_COUNT):
    mr_event_lineup = []
    for event_idx in range(MR_EVENT_START_IDX + relay * MR_POSITION_COUNT, MR_EVENT_START_IDX + (relay + 1) * MR_POSITION_COUNT):
        mr_pos_event_lineup = []
        for swimmer in lineup:
            mr_event_lineup.append(swimmer['events'][event_idx])
            mr_pos_event_lineup.append(swimmer['events'][event_idx])
        model.add(sum(mr_pos_event_lineup) <= 1)
    model.add_linear_expression_in_domain(sum(mr_event_lineup), 
    cp_model.Domain.from_values([0, 4]))

all_vars = [swimmer['events'][event_idx] for swimmer in lineup for event_idx in range(TOTAL_EVENT_COUNT)]

solver = cp_model.CpSolver()
solution_printer = cp_model.VarArraySolutionPrinter(all_vars)
# Enumerate all solutions.
solver.parameters.enumerate_all_solutions = True
# Solve.
status = solver.solve(model)
print(f"Number of solutions found: {solution_printer.solution_count()}")