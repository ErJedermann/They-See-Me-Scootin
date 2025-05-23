import json
import datetime
from pytz import timezone
import os
from os import listdir


# data format:
# {"data": [{
#     "type": "vehicle",
#     "id": "2d6d0399-ce58-4a0d-a95d-7522b5d35748",
#     "attributes": {
#         "state": "ACTIVE",
#         "lastLocationUpdate": "2023-09-30T21:22:03Z",
#         "lastStateChange": "2023-09-29T00:01:47Z",
#         "batteryLevel": 73,
#         "currentRangeMeters": 32000,
#         "lat": 49.441673,
#         "lng": 7.662921,
#         "maxSpeed": 20,
#         "zoneId": "KAISERSLAUTERN",
#         "code": 128150,
#         "iotVendor": "okai",
#         "licencePlate": "925WRX",
#         "isRentable": true,
#         "vehicleType": "escooter",
#         "hasHelmetBox": false,
#         "hasHelmet": false}
#     },

# load the .json files into a dict[id:scooter] where scooter is a dict with the attributes and the ID.


def filename_2_date(filename: str) -> (str, int) :
    # /home/eric/Lehre/TIER paper/data_2023_10_01/vehicles-20231001-000251.json
    filename = filename.split("/")[-1]
    if filename[0:8] != "vehicles":
        print(filename[0:8])
        raise Exception(f"Wrong filename, missing 'vehicles'! Expected 'vehicles-date-time.json', got: {filename}")
    if filename[-5:] != ".json":
        print(filename[-5:])
        raise Exception(f"Wrong filename, missing '.json'! Expected 'vehicles-date-time.json', got: {filename}")
    filename = filename[9:-5]
    time_object1 = datetime.datetime.strptime(filename, '%Y%m%d-%H%M%S')
    date_human = str(time_object1)
    utc_timestamp = int(time_object1.timestamp())
    return date_human, utc_timestamp

def llu_lsc_2_timestamp(time_string: str) -> int:
    # Datetime assumes it is local time, but it is utc, so we have to add the UTC-offset!
    time_object1 = datetime.datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%SZ')  # 2023-09-30T21:22:03Z
    time_object2 = datetime.datetime.fromtimestamp(time_object1.timestamp(), tz=timezone("Europe/Berlin"))
    time_object3 = datetime.datetime.fromtimestamp(time_object1.timestamp() + time_object2.utcoffset().seconds, tz=timezone("Europe/Berlin"))
    return time_object3.timestamp()


def load_scooters_from_json(filename: str) -> (int, dict):
    date_human, date_utc = filename_2_date(filename)
    json_file = open(filename)
    json_str = json_file.read()
    json_data = json.loads(json_str)
    scooters_lst = json_data['data']
    scooters_dict = {}
    for scooter_dict in scooters_lst:
        id = scooter_dict['id']
        attributes = scooter_dict['attributes']
        attributes['id'] = id
        attributes['collection_timestamp_human'] = date_human
        attributes['collection_timestamp_utc'] = date_utc
        attributes['lastLocationUpdate_timestamp'] = llu_lsc_2_timestamp(attributes['lastLocationUpdate'])
        attributes['lastStateChange_timestamp'] = llu_lsc_2_timestamp(attributes['lastStateChange'])
        scooters_dict[id] = attributes
    return date_utc, scooters_dict

def load_all_files(folder: str) -> [(int, dict)]:
    recordings_lst = [] # [(int, dict)]
    if not os.path.isdir(folder):
        raise Exception(f"Requires a folder!")
    if folder[-1] != "/":
        folder = folder + "/"
    all_folder_content = listdir(folder)
    for item in all_folder_content:
        full_filename = folder + item
        if not os.path.isfile(full_filename):
            continue
        if (item[-5:] == ".json") and (item[:8] == "vehicles"):
            date_utc, scooter_dict = load_scooters_from_json(full_filename)
            if type(date_utc) != int:
                print(f"WTF! {type(date_utc): {date_utc}}")
            recordings_lst.append((date_utc, scooter_dict))
    recordings_lst = sorted(recordings_lst, key=lambda x: x[0])
    return recordings_lst

def load_multiple_folders(folder_lst: [str]) -> [(int, dict)]:
    recordings_lst = []
    for folder in folder_lst:
        temp_lst = load_all_files(folder)
        recordings_lst.extend(temp_lst)
    recordings_lst = sorted(recordings_lst, key=lambda x: x[0])
    return recordings_lst


if __name__ == '__main__':
    my_file = "/home/eric/Lehre/TIER paper/data_2023_10_01/vehicles-20231001-000251.json"
    #my_file = "/home/eric/Lehre/TIER paper/data_2023_10_01/vehicles-20231001-090131.json"  # 2023-10-01T07:01:28Z  Δ=2:00:03
    #my_file = "/home/eric/Lehre/TIER paper/data_2023_10_01/vehicles-20231001-140116.json"  # 2023-10-01T12:01:06Z  Δ=2:00:10
    #my_file = "/home/eric/Lehre/TIER paper/data_2023_10_01/vehicles-20231001-122115.json"  # 2023-10-01T10:21:11Z  Δ=2:00:03
    #my_file = "/home/eric/Lehre/TIER paper/data_2023_10_01/vehicles-20231001-205555.json"  # 2023-10-01T18:55:51Z  Δ=2:00:04
    # -> the last-location-update-time is UTC, the collection-time is local!
    #my_folder = "/home/eric/Lehre/TIER paper/data_2023_10_01"
    #all_day = load_all_files(my_folder)
    #print(len(all_day))
    #print(all_day[0])
    time, scooters_dict = load_scooters_from_json(my_file)
    for key in list(scooters_dict.keys()):
        tmp_scooter = scooters_dict[key]
        print(tmp_scooter['lastLocationUpdate'])

