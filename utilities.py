import geopy


def __are_same_scooter_same_collection(scooter1: dict, scooter2: dict) -> bool:
    return (scooter1['collection_timestamp_utc'] == scooter2['collection_timestamp_utc'] and
            scooter1['lastLocationUpdate_timestamp'] == scooter2['lastLocationUpdate_timestamp'] and
            scooter1['lastStateChange_timestamp'] == scooter2['lastStateChange_timestamp'] and
            scooter1['lat'] == scooter2['lat'] and
            scooter1['lng'] == scooter2['lng'] and
            scooter1['batteryLevel'] == scooter2['batteryLevel'])

def __scooter_2_str(scooter) -> str:
    return (str(scooter['collection_timestamp_utc']) + str(scooter['lastLocationUpdate_timestamp']) +
            str(scooter['lastStateChange_timestamp']) + str(scooter['lat']) + str(scooter['lng']) +
            str(scooter['batteryLevel']))

def __reverse_multi_end_list(multi_end_trips: [(dict, [dict])]):
    # input: [(start_scooter_dict, [list_of_possible_end_scooter_dicts])]
    # output: [(end_scooter_dict, [list_of_possible_start_scooter_dicts])]
    end_scooters_dict = {}
    for start_scooter, end_scooters_lst in multi_end_trips:
        for end_scooter in end_scooters_lst:
            end_sc_str = __scooter_2_str(end_scooter)
            if end_sc_str in list(end_scooters_dict.keys()):
                end_entry, start_lst = end_scooters_dict[end_sc_str]
            else:
                end_entry = end_scooter
                start_lst = []
            start_lst.append(start_scooter)
            end_scooters_dict[end_sc_str] = (end_entry, start_lst)
    return list(end_scooters_dict.values())

def __filter_one_end_list(trip_candidates: [(dict, [dict])], verbose: bool = False) -> ([(dict, [dict])], [(dict, [dict])]):
    # input: [(start_scooter_dict, [list_of_possible_end_scooter_dicts])]
    input_len = len(trip_candidates)
    one_candidate_lst = []
    change_happened = True
    while change_happened:
        change_happened = False
        for i in range(len(trip_candidates)-1, -1, -1):
            if i >= len(trip_candidates):  # sometimes more than one trip are deleted in one iteration
                continue
            candidate = trip_candidates[i]
            cand_start, cand_end_lst = candidate
            if len(cand_end_lst) == 1:  # you found a trip with only one possible end. store it
                change_happened = True
                del trip_candidates[i]
                one_candidate_lst.append(candidate)
                # then go through the rest of the trip_candidates_lst and delete this end-node from all candidates-lists
                for j in range(len(trip_candidates)-1, -1, -1):
                    tmp_start, tmp_end_lst = trip_candidates[j]
                    for k in range(len(tmp_end_lst)-1, -1, -1):
                        if __are_same_scooter_same_collection(cand_end_lst[0], tmp_end_lst[k]):
                            if len(tmp_end_lst) == 1:  # if the list already has only one entry and you delete it, there is no end left, so delete the whole entry
                                if tmp_start['id'] == tmp_end_lst[k]['id']  and tmp_start['collection_timestamp_utc'] == tmp_end_lst[k]['collection_timestamp_utc']:
                                    print(f"Sanity-Warning: candidate_list_processing deletes a correct full trip")
                                del trip_candidates[j]
                                break
                            else:
                                if tmp_start['id'] == tmp_end_lst[k]['id'] and tmp_start['collection_timestamp_utc'] == tmp_end_lst[k]['collection_timestamp_utc']:
                                    print(f"Sanity-Warning: candidate_list_processing deletes a correct endpoint")
                                del tmp_end_lst[k]
    if verbose:
        print(f"input: {input_len}, output: 1-end: {len(one_candidate_lst)}, multi-end: {len(trip_candidates)}")
    return one_candidate_lst, trip_candidates



def find_trips_by_stable_state(trip_candidates: [(dict, [dict])], verbose: bool = False) -> ([(dict, [dict])], [(dict, [dict])]):
    one_candidate_lst = []
    input_len = len(trip_candidates)
    # step 3: find all trips with only one end candidate
    one_end_lst, multi_ends_lst = __filter_one_end_list(trip_candidates)
    if verbose:
        print(f"input-len: {input_len}, start-iteration: {len(one_end_lst)}/{len(multi_ends_lst)}")
    counter = 0
    while len(one_end_lst):
        counter += 1
        one_candidate_lst.extend(one_end_lst)
        # step 4: invert the lists (now they are in inverted order)
        multi_start_lst = __reverse_multi_end_list(multi_ends_lst)
        # step 5: repeat step 3: filter trips with only one start (since they are inverted, we find the start here)
        one_start_lst, multi_start_lst = __filter_one_end_list(multi_start_lst)
        if verbose:
            print(f"   iter {counter}a: single/multi: {len(one_start_lst)}/{len(multi_start_lst)}")
        one_end_lst = __reverse_multi_end_list(one_start_lst)  # to get the correct order, we have to invert them again
        one_candidate_lst.extend(one_end_lst)
        # step 5: repeat step 4: invert the list (now the multi-end-list is in the original order)
        multi_ends_lst = __reverse_multi_end_list(multi_start_lst)
        # step 5: repeat step 3: filter trips with only one end
        one_end_lst, multi_ends_lst = __filter_one_end_list(multi_ends_lst)
        if verbose:
            print(f"   iter {counter}b: single/multi: {len(one_end_lst)}/{len(multi_ends_lst)}")
    # step 6: return the lists
    if verbose:
        print(f"   input: {input_len} -> single/multi: {len(one_candidate_lst)}/{len(multi_ends_lst)}")
    return one_candidate_lst, multi_ends_lst

def geodetic_locations_2_dist(coord1_lat: float, coord1_long: float, coord2_lat: float, coord2_long: float) -> float:
    # https://stackoverflow.com/questions/19412462/getting-distance-between-two-points-based-on-latitude-longitude
    coords_1 = (coord1_lat, coord1_long)
    coords_2 = (coord2_lat, coord2_long)
    distance = geopy.distance.geodesic(coords_1, coords_2).km
    return distance

