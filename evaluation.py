import utilities

def print_trip_candidates_statistics(trip_candidates: [(dict, [dict])]):
    single_lst_correct = 0
    single_lst_wrong = 0
    multi_2lst_correct = 0
    multi_3lst_correct = 0
    multi_nlst_correct = 0
    multi_2lst_wrong = 0
    multi_3lst_wrong = 0
    multi_nlst_wrong = 0
    for start_scooter, end_scooters_lst in trip_candidates:
        list_len = len(end_scooters_lst)
        found_correct = False
        start_id = start_scooter['id']
        for end_candidate in end_scooters_lst:
            end_cand_id = end_candidate['id']
            if start_id == end_cand_id:
                found_correct = True
                break
        if found_correct:
            if list_len == 1:
                single_lst_correct += 1
            elif list_len == 2:
                multi_2lst_correct += 1
            elif list_len == 3:
                multi_3lst_correct += 1
            else:
                multi_nlst_correct += 1
        else:
            if list_len == 1:
                single_lst_wrong += 1
            elif list_len == 2:
                multi_2lst_wrong += 1
            elif list_len == 3:
                multi_3lst_wrong += 1
            else:
                multi_nlst_wrong += 1
    print(f"Check if start_id == end_id (or if start_id is in [end_ids])")
    print(f"   results of ({len(trip_candidates)}): "
          f"single_candidate_correct: {single_lst_correct} ({single_lst_correct/len(trip_candidates)*100:2.3f}%), "
          f"single_candidate_wrong: {single_lst_wrong} ({single_lst_wrong/len(trip_candidates)*100:2.3f}%), "
          f"multi_candidates_correct: {multi_2lst_correct+multi_3lst_correct+multi_nlst_correct} ({(multi_2lst_correct+multi_3lst_correct+multi_nlst_correct)/len(trip_candidates)*100:2.3f}%), "
          f"(2={multi_2lst_correct}, 3={multi_3lst_correct}, n={multi_nlst_correct}), "
          f"multi_candidates_wrong: {multi_2lst_wrong+multi_3lst_wrong+multi_nlst_wrong} ({(multi_2lst_wrong+multi_3lst_wrong+multi_nlst_wrong)/len(trip_candidates)*100:2.3f}%), "
          f"(2={multi_2lst_wrong}, 3={multi_3lst_wrong}, n={multi_nlst_wrong})")

def print_trip_distances(trip_identified: [(dict, [dict])], dist: float = 0.5):
    dist_less_n = 0
    dist_larger_n = 0
    for start_scooter, end_scooters_lst in trip_identified:
        start_lat = start_scooter["lat"]
        start_lng = start_scooter["lng"]
        end_lat = end_scooters_lst[0]["lat"]
        end_lng = end_scooters_lst[0]["lng"]
        beeline_dist = utilities.geodetic_locations_2_dist(start_lat, start_lng, end_lat, end_lng)  # [km]
        if beeline_dist < dist:
            dist_less_n += 1
        else:
            dist_larger_n += 1
    print(f"trips shorter/longer than {dist} km: {dist_less_n}/{dist_larger_n}")

def print_validation_estimatedOneEnd_vs_real_by_IDs(estimated_trips: [(dict, [dict])], real_trips: [dict]):
    correct_start_counter = 0
    correct_end_counter = 0
    for start_scooter, end_scooters_lst in estimated_trips:
        start_time = start_scooter["collection_timestamp_utc"]
        start_id = start_scooter["id"]
        end_time = end_scooters_lst[0]["collection_timestamp_utc"]
        end_id = end_scooters_lst[0]["id"]
        for real_tmp in real_trips:
            real_id = real_tmp['id']
            real_start_time = real_tmp['dataset_old']["collection_timestamp_utc"]
            real_end_time = real_tmp['dataset_new']["collection_timestamp_utc"]
            if real_id == start_id == end_id:
                if start_time == real_start_time:
                    correct_start_counter += 1
                    if end_time == real_end_time:
                        correct_end_counter += 1
                    break
    print(f"estimated_events:{len(estimated_trips)}, ground_truth:{len(real_trips)}, correct_end:{correct_end_counter}")

def print_validation_estimatedOneEnd_vs_real_by_distance(estimated_trips: [(dict, [dict])], real_trips: [dict], accept_dist_threshold: float = 0.05):
    correct_start_counter = 0
    correct_end_counter = 0
    for start_scooter, end_scooters_lst in estimated_trips:
        start_time = start_scooter["collection_timestamp_utc"]
        start_id = start_scooter["id"]
        end_lat = end_scooters_lst[0]['lat']
        end_lng = end_scooters_lst[0]['lng']
        for real_tmp in real_trips:
            real_id = real_tmp['id']
            real_start_time = real_tmp['dataset_old']["collection_timestamp_utc"]
            if real_id == start_id and start_time == real_start_time:
                correct_start_counter += 1
                real_end_lat = real_tmp['dataset_new']['lat']
                real_end_lng = real_tmp['dataset_new']['lng']
                beeline_end_dist = utilities.geodetic_locations_2_dist(end_lat, end_lng, real_end_lat, real_end_lng)  # [km]
                if beeline_end_dist < accept_dist_threshold:
                    correct_end_counter += 1
                    break
    print(f"estimated_events:{len(estimated_trips)}, ground_truth:{len(real_trips)}, correct_end:{correct_end_counter} (@{accept_dist_threshold*1000}m)")

def print_validation_estimatedMultiEnd_vs_real_by_distance(estimated_trips: [(dict, [dict])], real_trips: [dict], accept_dist_threshold: float = 0.05):
    correct_start_counter = 0
    correct_end_counter = 0
    for start_scooter, end_scooters_lst in estimated_trips:
        start_time = start_scooter["collection_timestamp_utc"]
        start_id = start_scooter["id"]
        end_found = False
        for real_tmp in real_trips:
            real_id = real_tmp['id']
            real_start_time = real_tmp['dataset_old']["collection_timestamp_utc"]
            if real_id == start_id and start_time == real_start_time:
                correct_start_counter += 1
                real_end_lat = real_tmp['dataset_new']['lat']
                real_end_lng = real_tmp['dataset_new']['lng']
                # go through the possible end_list
                for end_scooter in end_scooters_lst:
                    end_lat = end_scooter['lat']
                    end_lng = end_scooter['lng']
                    beeline_end_dist = utilities.geodetic_locations_2_dist(end_lat, end_lng, real_end_lat, real_end_lng)  # [km]
                    if beeline_end_dist < accept_dist_threshold:
                        correct_end_counter += 1
                        end_found = True
                        break
            if end_found:
                break
    print(f"multi_ends:{len(estimated_trips)}, ground_truth:{len(real_trips)}, correct_end:{correct_end_counter}")

