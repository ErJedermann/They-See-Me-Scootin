import datetime
import geopy.distance
import numpy as np
from matplotlib.pyplot import xlabel

import dataloader
import feature_analyzer
import plots
import pathfinder

def __lastlocupdate_2_utc(lastlocupdate: str) -> int:
    # "lastLocationUpdate": "2023-09-30T21:22:03Z",
    time_obj = datetime.datetime.strptime(lastlocupdate, '%Y-%m-%dT%H:%M:%SZ')
    return int(time_obj.timestamp())

def __geodetic_locations_2_dist(coord1_lat: float, coord1_long: float, coord2_lat: float, coord2_long: float) -> float:
    # https://stackoverflow.com/questions/19412462/getting-distance-between-two-points-based-on-latitude-longitude
    coords_1 = (coord1_lat, coord1_long)
    coords_2 = (coord2_lat, coord2_long)
    distance = geopy.distance.geodesic(coords_1, coords_2).km
    return distance

# 1. get a list of all IDs
# 2. for each ID go through all times and identify a disappearing-period
# 3. classify the disappearing-periods if they are a trip

def identify_trips_full_data(data_lst: [(int, dict)]) -> ([dict], [dict], [dict] ,[dict]):
    # data_list: [(utc_timestamp, {scooter_id: {attribute: value}}), (utc_timestamp, {...}), ...]
    # get a list of all IDs
    scooter_ids = set([])
    for (timestamp, scooters_dict) in data_lst:
        id_lst = list(scooters_dict.keys())
        id_set = set(id_lst)
        scooter_ids = scooter_ids.union(id_set)
    # for each ID go through all times and identify a disappearing-period
    disappearing_lst = []  # [(scooter_id, last_dataset_before_disappearing, re_appearing_dataset), ...]
    for scooter_id in scooter_ids:
        last_appearing_dataset = None
        was_visible = False
        for (timestamp, scooters_dict) in data_lst:
            id_lst = list(scooters_dict.keys())
            if last_appearing_dataset is None:
                if scooter_id in id_lst:  # the id shows up the first time
                    last_appearing_dataset = scooters_dict[scooter_id]
                    was_visible = True
            else:
                if scooter_id in id_lst and was_visible:  # it was visible, and still is
                    last_appearing_dataset = scooters_dict[scooter_id]
                elif scooter_id in id_lst and not was_visible:  # scooter re-appeared
                    disappearing_lst.append((scooter_id, last_appearing_dataset, scooters_dict[scooter_id]))
                    last_appearing_dataset = scooters_dict[scooter_id]
                    was_visible = True
                elif scooter_id not in id_lst and was_visible:  # it disappeared
                    was_visible = False
                elif scooter_id not in id_lst and not was_visible:  # it still is disappeared
                    was_visible = False
                else:
                    print(f"identify_trips_full_data: impossible case?!")
    # according to chapter 6.2.1 get the 'last location update' for calculating the trips duration
    # extract several features to identify a possible trip: beeline_distance, street_distance, duration, battery_change,
    #    street_velocity, beeline_velocity, battery_per_street_dist, battery_per_bee_dist, range_meter_delta
    events_lst = []  # list of dicts
    street_dist_loc_pairs = []
    for event in disappearing_lst:
        scooter_id, dataset_old, dataset_new = event
        feature_dict = {'id': scooter_id, 'dataset_old': dataset_old, 'dataset_new': dataset_new}
        collection_time_diff = dataset_new["collection_timestamp_utc"] - dataset_old["collection_timestamp_utc"]
        coll_time_2_loc_up_diff = dataset_new["lastLocationUpdate_timestamp"] - dataset_old["collection_timestamp_utc"]
        if coll_time_2_loc_up_diff < 0:
            trip_duration = collection_time_diff
        else:
            trip_duration = min(collection_time_diff, coll_time_2_loc_up_diff)  # Fixed Minimal Time Diff [sec]
        if trip_duration < 0:
            print(f"identify_trips_full_data: trip_duration<0?!")
        old_lat = dataset_old["lat"]
        old_long = dataset_old["lng"]
        new_lat = dataset_new["lat"]
        new_long = dataset_new["lng"]
        beeline_dist = __geodetic_locations_2_dist(old_lat, old_long, new_lat, new_long)  # [km]
        street_dist_loc_pairs.append((old_lat, old_long, new_lat, new_long))  # make the osmnx computation later with all routes at once (faster)
        battery_level_change = dataset_new["batteryLevel"] - dataset_old["batteryLevel"]  # [%]
        feature_dict['duration'] = trip_duration
        feature_dict['beeline_dist'] = beeline_dist
        feature_dict['beeline_velocity'] = beeline_dist / (trip_duration/3600)  # [km/h]
        feature_dict['battery_change'] = battery_level_change
        feature_dict['range_meter_delta'] = dataset_new["currentRangeMeters"] - dataset_old["currentRangeMeters"]  # [m]
        if beeline_dist == 0:
            feature_dict['street_bat_change'] = 0
            feature_dict['beeline_bat_change'] = 0
        else:
            feature_dict['beeline_bat_change'] = battery_level_change / beeline_dist  # [%/km]
        events_lst.append(feature_dict)
    # calculate the street_dist afterward in a bunch
    street_dist_lst = pathfinder.many_trip_dist(street_dist_loc_pairs)
    events_lst2 = []
    for i in range(len(street_dist_lst)):
        feature_dict = events_lst[i]
        street_dist = abs(street_dist_lst[i])/1000  # km
        trip_duration = feature_dict["duration"]
        feature_dict['street_dist'] = street_dist
        feature_dict['street_velocity'] = street_dist / (trip_duration / 3600)  # [km/h]
        if street_dist == 0:
            feature_dict['street_bat_change'] = 0
        else:
            battery_level_change = feature_dict["battery_change"]
            feature_dict['street_bat_change'] = battery_level_change / street_dist  # [%/km]
        events_lst2.append(feature_dict)

    # classify events by using the formulas from chapter 6.2.2:
    # trips:     (batteryChange ≤ 0 ∧ 4 ≤ dur ≤ 120 ∧ 500 ≤ distance ∧ speed ≤ 17 ∧ ( batt_dist ≤ − 1 ∨ ( batteryChange = 0 ∧ dist ≤ 1000 )) )
    # relocation:(batteryChange ≤ 0 ∧ 4 ≤ dur       ∧ 500 ≤ distance ∧ ( speed > 17 ∨ dur > 120 ∨ ( batt_dist > − 1 ∧ ( batteryChange != 0 ∨ dist > 1000 ))) )
    # roundtrip: (batteryChange ≤ 0 ∧ 4 ≤ dur ≤ 120 ∧ distance < 500)
    # loading:   (batteryChange > 0)
    trips = []
    roundtrips = []
    relocations = []
    loadings = []
    rest = []
    for feature_dict in events_lst2:
        battery_change = feature_dict['battery_change']  # [%]
        duration = feature_dict['duration']/60  # [min]
        distance = feature_dict['street_dist']*1000  # [m]
        speed = feature_dict['street_velocity']  # [km/h]
        battery_change_per_distance = feature_dict['street_bat_change']
        if duration > 2*60:
            continue
        if battery_change <= 0 and 4 <= duration <= 120 and distance >= 500 and speed <= 17 and (battery_change_per_distance <= -1 or (battery_change == 0 and distance <= 1000)):
            trips.append(feature_dict)
        elif battery_change <= 0 and 4 <= duration <= 120 and distance < 500:
            roundtrips.append(feature_dict)
        elif battery_change <= 0 and 4 <= duration and distance >= 500 and (speed > 17 or duration > 120 or (battery_change_per_distance > -1 and (battery_change != 0 or distance > 1000 ))):
            relocations.append(feature_dict)
        elif battery_change > 0:
            loadings.append(feature_dict)
        else:
            rest.append(feature_dict)
    return trips, relocations, roundtrips, loadings, rest

def plot_some_data(data_sets: dict[str, list[dict]], x_axis: str, y_axis: str, z_axis: str):
    my_plot_dict = {}
    for set_name in list(data_sets.keys()):
        temp_data_dict_lst = data_sets[set_name]
        data_list = []
        for i in range(len(temp_data_dict_lst)):
            temp_data_dict = temp_data_dict_lst[i]
            x = temp_data_dict[x_axis]
            y = temp_data_dict[y_axis]
            z = temp_data_dict[z_axis]
            data_list.append((x, y, z))
        data_list2 = np.array(data_list)
        print(f"set_name:{set_name}: "
              f"x=[{np.min(data_list2[:, 0])} - {np.max(data_list2[:, 0])}], "
              f"y=[{np.min(data_list2[:, 1])} - {np.max(data_list2[:, 1])}], "
              f"z=[{np.min(data_list2[:, 2])} - {np.max(data_list2[:, 2])}]")
        my_plot_dict[set_name] = data_list
    plots.plot_3D_data_dict(data_points_3D_dict=my_plot_dict, x_label='x: '+x_axis, y_label='y: '+y_axis, z_label='z: '+z_axis, figure_name="some interesting features")




if __name__ == '__main__':
    #my_folder = "/home/eric/Lehre/TIER paper/data_2023_10_01"
    #all_day = dataloader.load_all_files(my_folder)
    folder_lst = ["/home/eric/Lehre/TIER paper/tier_data/data_2023_10_01"]#, "/home/eric/Lehre/TIER paper/data_2024_03_01"]
    raw_scooter_data = dataloader.load_multiple_folders(folder_lst)
    trips, relocations, roundtrips, loadings, rest = identify_trips_full_data(raw_scooter_data)
    print(f"trips: {len(trips)}")
    print(f"relocations: {len(relocations)}")
    print(f"roundtrips: {len(roundtrips)}")
    print(f"loadings: {len(loadings)}")
    print(f"rest: {len(rest)}")
    data_dict = {'trips': trips, 'relocations': relocations, 'roundtrips': roundtrips, 'loadings': loadings, 'rest': rest}
    plot_some_data(data_dict, x_axis="street_dist", y_axis="street_velocity", z_axis="street_bat_change")
    plot_some_data(data_dict, x_axis="street_dist", y_axis="beeline_dist", z_axis="battery_change")
    plot_some_data(data_dict, x_axis="duration", y_axis="range_meter_delta", z_axis="battery_change")
    feature_analyzer.analyze_features(data_dict)
    feature_analyzer.analyze_loadings(loadings)
