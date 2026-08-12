import sys
from pathlib import Path

from common.utils import EVENT_MAP, INDIV_EVENT_COUNT, MR_EVENT_START_IDX, MR_POSITION_COUNT, RELAY_COUNT, TOTAL_EVENT_COUNT, FR2_START_IDX, FR4_START_IDX, FR_RELAY_COUNT
from lineup.powerpoints.calculate import calculate_relay_powerpoint, calculate_powerpoint_matrix

from ortools.sat.python import cp_model

"""
this file contains the utils for the lineup model
"""
def make_lineup(model, swimmers):
    """
    makes the lineup for the model
    Args:
        model: cpmodel, The model to add constraints to.
        swimmers: list of lists, The swimmers to make the lineup for.
    Returns:
        list of lists, The lineup for the model, each element of type boolvar
    """
    lineup = [] 
    for swimmer_idx in range(len(swimmers)):
        s_events = []
        for event_idx in range(TOTAL_EVENT_COUNT): 
            s_events.append(model.NewBoolVar(f"h_{swimmer_idx}_{event_idx}"))
        lineup.append(s_events)
    return lineup

def add_constraints(model, lineup, swimmers, times):
    """
    Add constraints to the model based on the planning doc and swim meet rules
    Args:
        model: cpmodel, The model to add constraints to.
    Returns:
        void--- but adds constraints to the model
    """

    ## constraints-- see planning doc for reference

    ## 1
    for event_idx in range(INDIV_EVENT_COUNT): 
        event_lineup = []
        for swimmer in lineup:
            event_lineup.append(swimmer[event_idx])
        model.add(sum(event_lineup) >= 1)
        model.add(sum(event_lineup) <= 3)

    ## 2 and 3
    for swimmer in lineup:
        indiv_events = []
        total_events = []
        for event_idx in range(TOTAL_EVENT_COUNT):
            total_events.append(swimmer[event_idx])
            if event_idx < INDIV_EVENT_COUNT:
                indiv_events.append(swimmer[event_idx])

        model.add(sum(total_events) <= 4)
        model.add(sum(indiv_events) <= 2)

    ## 4a.
    used_fr = []
    for event_idx in range(INDIV_EVENT_COUNT, MR_EVENT_START_IDX):  
        u = model.NewBoolVar(f"u_{event_idx}")
        used_fr.append(u)
        fr_event_lineup = []
        for swimmer in lineup:
            fr_event_lineup.append(swimmer[event_idx])
        model.add_linear_expression_in_domain(sum(fr_event_lineup), 
        cp_model.Domain.from_values([0, 4]))
        model.add(sum(fr_event_lineup) == 4).OnlyEnforceIf(u)
        model.add(sum(fr_event_lineup) == 0).OnlyEnforceIf(u.Not())
    for i in range(FR_RELAY_COUNT):
        for event_idx in range(i * RELAY_COUNT, (i + 1) * RELAY_COUNT-1):
            model.AddImplication(used_fr[event_idx+1], used_fr[event_idx ])



    ## todo: 5a, 5b
    for swimmer in lineup:
        fr_relay = []
        mr_relay = []
        for event_idx in range(INDIV_EVENT_COUNT, MR_EVENT_START_IDX):
            fr_relay.append(swimmer[event_idx])
        for event_idx in range(MR_EVENT_START_IDX, TOTAL_EVENT_COUNT):
            mr_relay.append(swimmer[event_idx])
        model.add(sum(fr_relay) <= 1)
        model.add(sum(mr_relay) <= 1)


    ## 4b, 6
    used_mr = []
    for relay in range(RELAY_COUNT):
        mr_event_lineup = []
        u = model.NewBoolVar(f"u_{MR_EVENT_START_IDX + relay}")
        used_mr.append(u)
        for event_idx in range(MR_EVENT_START_IDX + relay * MR_POSITION_COUNT, MR_EVENT_START_IDX + (relay + 1) * MR_POSITION_COUNT):
            mr_pos_event_lineup = []
            for swimmer in lineup:
                mr_event_lineup.append(swimmer[event_idx])
                mr_pos_event_lineup.append(swimmer[event_idx])
            model.add(sum(mr_pos_event_lineup) <= 1)
        model.add_linear_expression_in_domain(sum(mr_event_lineup), 
        cp_model.Domain.from_values([0, 4]))
        model.add(sum(mr_event_lineup) == 4).OnlyEnforceIf(u)
        model.add(sum(mr_event_lineup) == 0).OnlyEnforceIf(u.Not())
    for i in range(len(used_mr) - 1):
        model.AddImplication(used_mr[i + 1], used_mr[i])

    #7a -- time(a relay) <= time (b relay) <= time (c relay) for free relays
    for i in range(FR_RELAY_COUNT):
        relay_times_fr = []
        for relay in range(FR2_START_IDX + i * RELAY_COUNT, FR2_START_IDX + (i + 1) * RELAY_COUNT):
            time = []
            for swimmer_idx in range(len(swimmers)):
                time_rounded = int(round(times[swimmer_idx][relay] * 100)) ## round time and scale by 100 for cpsat
                time.append(lineup[swimmer_idx][relay] * time_rounded)
            relay_times_fr.append(sum(time))
        for j in range(len(relay_times_fr) - 1): 
            model.add((relay_times_fr[j] <= relay_times_fr[j + 1])).only_enforce_if(used_fr[j+ i*RELAY_COUNT], used_fr[j+ i*RELAY_COUNT + 1]) ## only enforce if both relays are used

    #7b -- time(a relay) <= time (b relay) <= time (c relay) for medley relays
    relay_times_mr = []
    for i in range(RELAY_COUNT):
        time = []
        for event_idx in range(MR_EVENT_START_IDX + i * MR_POSITION_COUNT, MR_EVENT_START_IDX + (i + 1) * MR_POSITION_COUNT):
            for swimmer_idx in range(len(swimmers)):
                time_rounded = int(round(times[swimmer_idx][event_idx] * 100)) ## round time and scale by 100 for cpsat
                time.append(lineup[swimmer_idx][event_idx] * time_rounded)
        relay_times_mr.append(sum(time))
    for i in range(len(relay_times_mr) - 1):
        model.add(relay_times_mr[i] <= relay_times_mr[i + 1]).only_enforce_if(used_mr[i], used_mr[i+1]) ## only enforce if both relays are used


def maximize_powerpoints(model, lineup, swimmers, times, gender):
    """
    makes the objective function to maximize powerpoints
    Args:
        model: cpmodel, The model to add constraints to.
        lineup: list of lists, The lineup to maximize powerpoints for.
        swimmers: list of lists, The swimmers to maximize powerpoints for.
        times: list of lists, The times of the swimmers for each event
        gender: str, the gender of the swimmers
    Returns:
        void--- but adds the objective function to the model
    """
    pp = calculate_powerpoint_matrix(gender, times)
    powerpoints = sum([pp[s][e] * lineup[s][e] for s in range(len(swimmers)) for e in range(INDIV_EVENT_COUNT)]) ## individual event powerpoints

    ## disclaimer : relay powerpoint calculations are approximations of the actual powerpoint system because im lazy
    ## its not exactly cubic inverse, but it still attempts to reward faster aggregated relay times

    ## 200 FR powerpoints
    for i in range(RELAY_COUNT):
        e = FR2_START_IDX + i
        x = sum(lineup[s][e] * pp[s][e] * (RELAY_COUNT - i) for s in range(len(swimmers)))
        powerpoints += x

    ## 400 FR powerpoints
    for i in range(RELAY_COUNT):
        e = FR4_START_IDX + i
        x = sum(lineup[s][e] * pp[s][e] * (RELAY_COUNT - i) for s in range(len(swimmers)))
        powerpoints += x

    ## 200 MR powerpoints
    for i in range(RELAY_COUNT):
        x = sum(lineup[s][e] * pp[s][e] * (RELAY_COUNT - i) for s in range(len(swimmers)) for e in range(MR_EVENT_START_IDX + i * MR_POSITION_COUNT, MR_EVENT_START_IDX + (i + 1) * MR_POSITION_COUNT))
        powerpoints += x

    model.maximize(powerpoints)


