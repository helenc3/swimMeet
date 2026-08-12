import csv
from pathlib import Path

from common.mongodb.queries2 import get_times_matrix
from common.mongodb.connect import connect_to_mongodb
from common.utils import EVENT_MAP
from lineup.powerpoints.calculate import calculate_powerpoint_matrix

"""
this is a testing script mainly for the methods in the queries2.py and calculate.py (see imports)
writes the times and powerpoint matrices to csv files in the out_dir
see the files in this directory for examples.
"""

client, db = connect_to_mongodb()
season = "2025-2026"
team = "Princeton"
gender = "female"

swimmers, times_matrix = get_times_matrix(db, season, team)
powerpoint_matrix = calculate_powerpoint_matrix(gender, times_matrix)

out_dir = Path(__file__).resolve().parent
event_names = [EVENT_MAP[i] for i in range(len(EVENT_MAP))]


def fmt(val):
    if val is None:
        return ""
    return f"{float(val):.2f}"


def write_matrix_csv(path, swimmers, matrix, event_names):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["swimmer", *event_names])
        for name, row in zip(swimmers, matrix):
            writer.writerow([name, *[fmt(v) for v in row]])


write_matrix_csv(out_dir / "times_matrix.csv", swimmers, times_matrix, event_names)
write_matrix_csv(out_dir / "powerpoint_matrix.csv", swimmers, powerpoint_matrix, event_names)

print(f"Wrote {out_dir / 'times_matrix.csv'}")
print(f"Wrote {out_dir / 'powerpoint_matrix.csv'}")