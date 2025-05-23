import geopy.distance
import json

import dataloader
import trip_extractor_full_data
import evaluation
import utilities


def __geodetic_locations_2_dist(coord1_lat: float, coord1_long: float, coord2_lat: float, coord2_long: float) -> float:
    # https://stackoverflow.com/questions/19412462/getting-distance-between-two-points-based-on-latitude-longitude
    coords_1 = (coord1_lat, coord1_long)
    coords_2 = (coord2_lat, coord2_long)
    distance = geopy.distance.geodesic(coords_1, coords_2).km
    return distance

def sanitize_data(loaded_data_with_id: [(int, dict)]) -> [(int, [dict])]:
    # convert from a list of (timestamps, dict[scooter_ID, scooter_data]) to a list of (timestamp, [scooter_data])
    # (where scooter_data is also a dict). For sanity-checking the scooters keep their IDs inside
    output_lst = []
    for element in loaded_data_with_id:
        timestamp, all_scooters_dict = element
        all_scooters_lst = list(all_scooters_dict.values())
        output_lst.append((timestamp, all_scooters_lst))
    return output_lst

def remove_standing_scooters(scooters_t1: [dict], scooters_t2: [dict], verbose: bool = False) -> ([dict], [dict]):
    # TODO: optimize this to make it faster for larger data-analysis (numpy vectorization for dist-calculation)
    # 1. remove scooters that are just standing around. for each scooter at t1 find the scooter at t2 with minimal distance:
    #   if (min_dist < GPS_inaccuracy) and (battery-level is the same) and (lastLocationUpdate is same) this is the same scooter
    threshold_gps_accuracy = 0.002  # 2m
    perfect_standing_deletions = 0
    standing_deletions = 0
    # first remove all perfect still standing scooters (the majority)
    if verbose:
        print(f"remove standing scooters (perfect):")
    for i in range(len(scooters_t1)-1, -1, -1):  # go backwards to avoid skipping + out of bounds when removing items
        if verbose:
            if i%100 == 0:
                print(f"{i}/{len(scooters_t1)}")
        scooter_1 = scooters_t1[i]
        lat1 = scooter_1["lat"]
        lng1 = scooter_1["lng"]
        llu1 = scooter_1["lastLocationUpdate"]
        lsc1 = scooter_1['lastStateChange_timestamp']
        for j in range(len(scooters_t2)-1, -1, -1):
            scooter_2 = scooters_t2[j]
            lat2 = scooter_2["lat"]
            lng2 = scooter_2["lng"]
            llu2 = scooter_2["lastLocationUpdate"]
            lsc2 = scooter_2['lastStateChange_timestamp']
            dist = __geodetic_locations_2_dist(lat1, lng1, lat2, lng2)
            if dist == 0 and llu1 == llu2 and lsc1 == lsc2:  # you found the scooter obviously
                if scooters_t1[i]['id'] != scooters_t2[j]['id']:  # sanity-checking
                    print("Sanity-Warning: remove_standing_scooters() removes perfect scooters with not the same ID!")
                del scooters_t1[i]
                del scooters_t2[j]
                perfect_standing_deletions += 1
                break
    # than remove the standing but GPS-error scooters
    if verbose:
        print(f"remove standing scooters (GPS):")
    for i in range(len(scooters_t1)-1, -1, -1):
        if verbose:
            if i%100 == 0:
                print(f"{i}/{len(scooters_t1)}")
        scooter_1 = scooters_t1[i]
        lat1 = scooter_1["lat"]
        lng1 = scooter_1["lng"]
        bat1 = scooter_1["batteryLevel"]
        lsc1 = scooter_1['lastStateChange_timestamp']
        best_candidate_index = None
        best_candidate_dist = 999
        for j in range(len(scooters_t2)-1, -1, -1):
            scooter_2 = scooters_t2[j]
            lat2 = scooter_2["lat"]
            lng2 = scooter_2["lng"]
            bat2 = scooter_2["batteryLevel"]
            lsc2 = scooter_2['lastStateChange_timestamp']
            dist = __geodetic_locations_2_dist(lat1, lng1, lat2, lng2)
            if dist < best_candidate_dist and abs(bat1 - bat2) < 2 and lsc1 == lsc2:  # you found a better candidate
                best_candidate_index = j
                best_candidate_dist = dist
        if best_candidate_dist < threshold_gps_accuracy:  # you found a scooter that did not move
            if scooters_t1[i]['id'] != scooters_t2[best_candidate_index]['id']:  # sanity-checking
                print("Sanity-Warning: remove_standing_scooters() removes GPS-moved scooters with not the same ID!")
                print(f"     scooter_old: {scooters_t1[i]}")
                print(f"     scooter_new: {scooters_t2[best_candidate_index]}")
            del scooters_t1[i]
            del scooters_t2[best_candidate_index]
            standing_deletions += 1
    if verbose:
        print(f"remove perfect_standing:{perfect_standing_deletions}, standing:{standing_deletions}")
    return scooters_t1, scooters_t2

def remove_slightly_moving_scooters(scooters_t1: [dict], scooters_t2: [dict], verbose: bool = False) -> ([dict], [dict]):
    # 2. remove scooters that are just moved a few meters in a short period of time (between two collection times t1 and t2)
    threshold_gps_accuracy = 0.002  # 2m
    threshold_movement = 0.5  # 500m
    moved_deletions = 0
    for i in range(len(scooters_t1) - 1, -1, -1):  # go backwards to avoid skipping + out of bounds when removing items
        scooter_1 = scooters_t1[i]
        lat1 = scooter_1["lat"]
        lng1 = scooter_1["lng"]
        bat1 = scooter_1["batteryLevel"]
        lsc1 = scooter_1['lastStateChange_timestamp']
        cts1 = scooter_1['collection_timestamp_utc']
        best_candidate_index = None
        best_candidate_dist = 999
        for j in range(len(scooters_t2) - 1, -1, -1):
            scooter_2 = scooters_t2[j]
            lat2 = scooter_2["lat"]
            lng2 = scooter_2["lng"]
            bat2 = scooter_2["batteryLevel"]
            llu2 = scooter_2["lastLocationUpdate_timestamp"]
            lsc2 = scooter_2['lastStateChange_timestamp']
            cts2 = scooter_2['collection_timestamp_utc']
            dist = __geodetic_locations_2_dist(lat1, lng1, lat2, lng2)
            if dist < threshold_movement:
                time_diff = llu2 - cts1
                if time_diff < 1:
                    time_diff = cts2 - cts1
                speed = dist / time_diff * 3600  # [km/h]
                if dist < best_candidate_dist and bat1 - bat2 < 3 and lsc1 == lsc2 and speed < 17:
                    best_candidate_index = j
                    best_candidate_dist = dist
        if best_candidate_index is not None:
            if scooters_t1[i]['id'] != scooters_t2[best_candidate_index]['id']:  # sanity-checking
                print("Sanity-Warning: remove_slightly_moving_scooters() removes scooters with not the same ID!")
            del scooters_t1[i]
            del scooters_t2[best_candidate_index]
            moved_deletions += 1
    if verbose:
        print(f"remove_slightly_moving_scooters deletions:{moved_deletions}")
    return scooters_t1, scooters_t2

def __ground_truth_find_scooters_in_both_sets(scooters_t1: [dict], scooters_t2: [dict]):
    scooters_in_both = []
    for scooter_1 in scooters_t1:
        id1 = scooter_1['id']
        for scooter_2 in scooters_t2:
            id2 = scooter_2['id']
            if id1 == id2:
                dist = __geodetic_locations_2_dist(scooter_1['lat'], scooter_1['lng'], scooter_2['lat'], scooter_2['lng'],)
                bat_delta = scooter_1['batteryLevel'] - scooter_2['batteryLevel']
                entry = (id1, dist, bat_delta)
                scooters_in_both.append(entry)
                break
    if len(scooters_in_both) > 0:
        print(f"ground-truth number of scooters in both sets: {len(scooters_in_both)}: {scooters_in_both}")

def make_appearing_disappearing_lists(collection_lst: [(int, [dict])], verbose: bool = True) -> ([(int, [dict])], [(int, dict)]):
    appear_lst = []
    disappear_lst = []
    # do some collection-to-collection removals of standing scooters
    for i in range(len(collection_lst)-1):
        if verbose:
            print(f"collection {i+1}/{len(collection_lst)}")
        time1, lst1 = collection_lst[i]
        time2, lst2 = collection_lst[i+1]
        lst1 = lst1[:]  # make a copy of the lists (no deepcopy required, just a new list)
        lst2 = lst2[:]
        lst1, lst2 = remove_standing_scooters(lst1, lst2, verbose=False)
        lst1, lst2 = remove_slightly_moving_scooters(lst1, lst2, verbose=True)
        if verbose:
            print(f"lst1: {len(lst1)}, lst2: {len(lst2)}")
        __ground_truth_find_scooters_in_both_sets(lst1, lst2)
        disappear_lst.append((time1, lst1))
        appear_lst.append((time2, lst2))
    return appear_lst, disappear_lst

def safe_appearing_disappearing_lists(appear_lst: [(int, [dict])], disappear_lst: [(int, [dict])], filename: str):
    my_lists = (appear_lst, disappear_lst)
    with open(filename, 'w') as file:
        json.dump(my_lists, file)

def load_appearing_disappearing_lists(filename: str) -> ([(int, [dict])], [(int, [dict])]):
    file = open(filename)
    my_lists = json.load(file)
    return my_lists

def remove_loading_scooters(appear_lst: [(int, [dict])], disappear_lst: [(int, [dict])], verbose: bool = False) -> ([(int, [dict])], [(int, [dict])]):
    # if a scooter appears after any time with 100% battery, it was loaded
    # info: when a loading happened, there is always a state-change in the last 3 minutes! so there is never the same lsc-timestamp.
    loading_deletions = 0
    GPS_inaccuracy = 0.001  # 1m
    for timestamp_new, scooters_lst_new in appear_lst:
        for i in range(len(scooters_lst_new)-1, -1, -1):
            scooter_new = scooters_lst_new[i]
            if scooter_new['batteryLevel'] < 98:  # consider only fresh, fully loaded scooters. not interesting for now
                continue
            # if a scooter was loaded, figure out when the last state-change happened
            cts_new = scooter_new['collection_timestamp_utc']
            lsc_new = scooter_new['lastStateChange_timestamp']
            # find if there is a disappearing scooter in the past, that has exactly the same location but a much lower battery (and maybe the same lsc?)
            lat_new = scooter_new["lat"]
            lng_new = scooter_new["lng"]
            llu_new = scooter_new["lastLocationUpdate_timestamp"]
            for timestamp_old, scooters_lst_old in disappear_lst:
                if timestamp_old >= timestamp_new:  # disappearing scooters from the future are not interesting. stop here
                    break
                did_delete = False
                for j in range(len(scooters_lst_old)-1, -1, -1):
                    scooter_old = scooters_lst_old[j]
                    if scooter_old['batteryLevel'] > 40:  # those have too much energy for being loaded (some were loaded with 39%)
                        continue
                    lat_old = scooter_old["lat"]
                    lng_old = scooter_old["lng"]
                    llu_old = scooter_old["lastLocationUpdate_timestamp"]
                    lsc_old = scooter_old['lastStateChange_timestamp']
                    cts_old = scooter_old['collection_timestamp_utc']
                    dist = __geodetic_locations_2_dist(lat_new, lng_new, lat_old, lng_old)  # [km]
                    if dist < GPS_inaccuracy:  # this is the same scooter
                        # the properties cts_new-lsc_new < 4*60 and cts_old < lsc_new hold always, so they are not useful for distinguishing
                        if scooters_lst_new[i]['id'] != scooters_lst_old[j]['id']:  # sanity-checking
                            print(f"Sanity-Warning: remove_loading_scooters() removes scooters with not the same ID!")
                            print(f"                lsc_old: {lsc_old}, llu_old: {llu_old}, cts_old: {cts_old}, llu_new: {llu_new}, lsc_new: {lsc_new}, cts_new: {cts_new}")
                        del scooters_lst_new[i]
                        del scooters_lst_old[j]
                        loading_deletions += 1
                        did_delete = True
                        break
                if did_delete:
                    break
    if verbose:
        print(f"remove_loading_scooters:{loading_deletions}")
    return appear_lst, disappear_lst

def find_scooter_trip_candidates(appear_lst: [(int, [dict])], disappear_lst: [(int, [dict])], verbose: bool = False) -> [(dict, [dict])]:
    # returns a list of pairs: start_scooters (from disappear_lst) and list of possible end_scooters (from apprear_lst)
    trip_candidates = []
    velocity_errors = 0
    battery_errors = 0
    battery_roundtrip = 0
    lsc_errors = 0
    wrong_candidates = 0
    missing_correct_candidate = 0
    uniquely_identified = 0
    last_timestamp, _ = appear_lst[-1]
    # do a fist estimation which scooters could be roughly interesting
    for timestamp_start, scooters_lst_start in disappear_lst:
        for start_scooter in scooters_lst_start:
            this_candidates_lst = []
            lat_start = start_scooter["lat"]
            lng_start = start_scooter["lng"]
            bat_start = start_scooter['batteryLevel']
            cts_start = start_scooter['collection_timestamp_utc']
            lsc_start = start_scooter['lastStateChange_timestamp']
            for timestamp_end, scooters_lst_end in appear_lst:
                if timestamp_start >= timestamp_end:  # trips can not end in the past or now (they have to end in the future)
                    continue
                if timestamp_start + 2*3600 < timestamp_end:  # the maximal duration of a trip is 2h
                    continue
                for end_scooter in scooters_lst_end:
                    lat_end = end_scooter["lat"]
                    lng_end = end_scooter["lng"]
                    bat_end = end_scooter['batteryLevel']
                    cts_end = end_scooter['collection_timestamp_utc']
                    lsc_end = end_scooter['lastStateChange_timestamp']
                    llu_end = end_scooter["lastLocationUpdate_timestamp"]
                    beeline_dist = __geodetic_locations_2_dist(lat_start, lng_start, lat_end, lng_end)  # [km]
                    bat_change_real = bat_start - bat_end  # [%]
                    bat_change_expected = round(beeline_dist * 2)  # all 500m the battery drops about 1%
                    t1 = llu_end - cts_start
                    t2 = cts_end - cts_start
                    if t1 < 1:
                        duration = t2  # [sec]
                    else:
                        duration = min(t1, t2)  # [sec]
                    velocity = beeline_dist / duration * 3600  # [km/h]
                    if velocity > 17:
                        if start_scooter['id'] == end_scooter['id']:
                            velocity_errors += 1
                        continue
                    if bat_change_real < bat_change_expected - 3:  # if real bat-usage is much smaller than expected (-buffer) - this can not be
                        bat_lvl_full = 100 - bat_change_expected - 3  # 100% - expected - buffer
                        lsc_changed_recently = cts_start < lsc_end < cts_end
                        if bat_end > bat_lvl_full and lsc_changed_recently:  # if the battery was loaded directly before or after the trip was done, this is acceptable
                            pass
                        else:
                            if start_scooter['id'] == end_scooter['id']:
                                battery_errors += 1
                            continue
                    if bat_change_real > bat_change_expected + 3:  # if the bat-usage is much larger than expected (+buffer) - this is a roundtrip
                        if start_scooter['id'] == end_scooter['id']:
                            battery_roundtrip += 1
                        continue
                    if lsc_start != lsc_end:
                        found_another_explanation = False
                        # rarely a state-change happens during a renting. re-calculate the velocity if this can be correct.
                        if llu_end == lsc_end:
                            # in this case the state-change happened at the end of the trip
                            velocity_2a = beeline_dist / (cts_start-llu_end) * 3600
                        else:
                            # in this case, the state-change happened at the start of the trip
                            velocity_2a = beeline_dist / (llu_end - lsc_end) * 3600
                        lsc_changed_2a = cts_start < lsc_end <= llu_end < cts_end
                        if velocity_2a < 17 +1 and lsc_changed_2a :
                            found_another_explanation = True
                        # if a loading happened directly before or after the trip
                        bat_lvl_full = 100 - bat_change_expected - 3  # 100% - expected - buffer
                        lsc_changed_recently = cts_start < lsc_end < cts_end
                        if bat_end > bat_lvl_full and lsc_changed_recently:
                            found_another_explanation = True
                        # check if another explanation was found
                        if not found_another_explanation:
                            if start_scooter['id'] == end_scooter['id']:
                                lsc_errors += 1
                            continue
                    # consider it a possible candidate for a trip
                    if start_scooter['id'] != end_scooter['id']:
                        wrong_candidates += 1
                    this_candidates_lst.append(end_scooter)
            if len(this_candidates_lst) > 0:
                found_correct = False
                for cand in this_candidates_lst:
                    if cand['id'] == start_scooter['id']:
                        found_correct = True
                        if len(this_candidates_lst) == 1:
                            uniquely_identified += 1
                        break
                if not found_correct:
                    missing_correct_candidate += 1
                trip_candidates.append((start_scooter, this_candidates_lst))
    if verbose:
        print(f"velocity_errors: {velocity_errors}, battery_errors:{battery_errors}, battery_roundtrip: {battery_roundtrip}, lsc_errors:{lsc_errors}, wrong_candidates: {wrong_candidates}, missing_correct_candidate: {missing_correct_candidate}, uniquely_identified: {uniquely_identified}")
    return trip_candidates

if __name__ == '__main__':
    # The steps are according to the algorithm in section 6 of the paper.
    # Before starting the stuff from scratch (to generate new lists), make sure to unzip the data folders.
    # step 0.a: specify the data to load
    dates_lst = ["2023_10_01", "2023_10_24", "2023_11_15", "2023_12_18", "2024_01_04", "2024_03_09", "2024_03_16"]
    used_date = dates_lst[0]  # change the number to load the other days: [0-6]
    load_folder = "data/data_"+used_date
    safe_file = "data/dis_appearing_lsts_"+used_date+".json"
    print(f"load: {load_folder}")

    # step 0.b: load the data and calculate the appearing/disappearing scooters, then store them in a file
    # all_day = dataloader.load_all_files(load_folder)
    # all_day = sanitize_data(all_day)
    # appearing_lst, disappearing_lst = make_appearing_disappearing_lists(all_day)  # this step takes some time 16:22 -
    # safe_appearing_disappearing_lists(appearing_lst, disappearing_lst, safe_file)

    # step 0.c: if the file is already available, you can simply load it (saves a lot of time)
    appearing_lst, disappearing_lst = load_appearing_disappearing_lists(safe_file)

    # step 1: remove loading scooters over any time period (ok... step 1 from the paper is included in step 2 in the
    #         code, but this is something else we can filter out before)
    appearing_lst, disappearing_lst = remove_loading_scooters(appearing_lst, disappearing_lst, verbose=True)

    # step 2: find all possible trip candidates, based on the constraints (max 2h, max 17km/h, ...)
    trip_candidates_lst = find_scooter_trip_candidates(appearing_lst, disappearing_lst, verbose=True)
    print("")
    print(f"mid-term evaluation (how many trips were easy to identify, what is the remaining potential):")
    evaluation.print_trip_candidates_statistics(trip_candidates_lst)

    # steps 3-6: identify the trips where only one possible end-candidate is available
    trips_identified, trip_candidates_lst = utilities.find_trips_by_stable_state(trip_candidates_lst, verbose=True)

    # evaluate the results
    print("")
    print(f"final evaluation (part 1/2):")
    trip_candidates_lst.extend(trips_identified)  # combine them to have all together for the overfiew
    evaluation.print_trip_candidates_statistics(trip_candidates_lst)
    evaluation.print_trip_distances(trips_identified, dist=0.5)

    # compare to ground_truth_tips
    print("")
    print(f"final evaluation (part 2/2: load fresh data, identify all events, compare the found trips):")
    all_day = dataloader.load_all_files(load_folder)
    trips, relocations, roundtrips, loadings, rest = trip_extractor_full_data.identify_trips_full_data(all_day)
    print(f"trips:")
    evaluation.print_validation_estimatedOneEnd_vs_real_by_IDs(trips_identified, trips)
    print(f"re-locations:")
    evaluation.print_validation_estimatedOneEnd_vs_real_by_IDs(trips_identified, relocations)
    print(f"round-trips:")
    evaluation.print_validation_estimatedOneEnd_vs_real_by_IDs(trips_identified, roundtrips)
    print(f"loadings:")
    evaluation.print_validation_estimatedOneEnd_vs_real_by_IDs(trips_identified, loadings)
    print(f"undefined:")
    evaluation.print_validation_estimatedOneEnd_vs_real_by_IDs(trips_identified, rest)

