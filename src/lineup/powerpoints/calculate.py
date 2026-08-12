import json
import numpy as np
from common.utils import BASE_TIMES_FILE, EVENT_MAP, INDIV_EVENT_COUNT, MR_EVENT_START_IDX, MR_POSITION_COUNT, MR_RELAY_COUNT, TOTAL_EVENT_COUNT


def load_basetimes(basetimes_file):
    """
    Load the basetimes from the file.
    args:
        basetimes_file: str, the file name of the basetimes file
    returns:
        dict, basetimes[gender][event] = time
    """
    with open(basetimes_file, 'r') as f:
        basetimes = json.load(f)
    return basetimes

def calculate_powerpoint_matrix(gender, times, event_map = EVENT_MAP, basetimes_file = BASE_TIMES_FILE):
    """
    Calculate the powerpoint matrix for a given gender and times.
    uses the formula: powerpoint = (basetime/time)^3 *1000
    in short its just a matrix transpose of the times array

    args: 
        gender: str, the gender of the swimmer
        times: 2d arr times[swimmer][event] = time
        event_map: dict, event_map[index] = event name
        event map length should equal the number of events in the times array
        basetimes_file: str, the file name of the basetimes file

    returns:
        2d array powerpoints[swimmer][event] = powerpoint (int, rounded to the nearest integer)
    """

    basetimes = load_basetimes(basetimes_file)[gender]
    pp = []
    for swimmer_idx in range(len(times)):
        swimmer_pp = []
        for event_idx in event_map:
            event_name = event_map[event_idx]
            basetime = basetimes[event_name]
            time = times[swimmer_idx][event_idx]
            calculation = (basetime/time)**3 * 1000
            calculation = int(round(calculation)) ## round to nearest integer for cpsat
            swimmer_pp.append(calculation)
        pp.append(swimmer_pp)
    return pp # list of lists --- i might consider changing this to a numpy array later

def calculate_relay_powerpoint(gender, time, relay_event, basetimes_file = BASE_TIMES_FILE):
    """
    calculate the powerpoint for a relay event
    args:
        gender: str, the gender of the swimmers
        time: float, the time of the relay
        relay_event: str, the relay event name, (200 MR, 200 FR, 400 FR)
        basetimes_file: str, the file name of the basetimes file
    returns:
        int, the powerpoint for the relay event, rounded to the nearest integer
    """
    basetimes = load_basetimes(basetimes_file)[gender]
    basetime = basetimes[relay_event]
    calculation = (basetime/time)**3 * 1000
    calculation = int(round(calculation)) ## round to nearest integer for cpsat
    return calculation
