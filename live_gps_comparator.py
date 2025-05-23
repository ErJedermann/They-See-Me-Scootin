import gpxpy
import gpxpy.gpx
import json
import plotly.graph_objects as go
import numpy as np

def load_gpx_data(filename: str) -> [(float, float)]:
    """Loads a .gpx-track.
    Args:
        filename (str): Name/Path of the file to open.
    Returns:
         [(float, float)]: List of (lat, lng).
    """
    gpx_f = open(filename, 'r')
    gpx = gpxpy.parse(gpx_f)
    if len(gpx.tracks) > 1:
        print(f"WARNING: more than one gpx-track found, only fist one loaded.")
    my_lst = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                my_lst.append((float(point.latitude),float(point.longitude)))
    return my_lst

def load_json_data(filename: str) -> dict[str,list[(float, float)]]:
    """Loads scooter tracks from .json file.
    Args:
        filename (str): Name/Path of the file to open.
    Returns:
        dict[str,list[(float, float)]]: Dict of {scooter_id: list_of_locations[(lat, lng)]}
            """
    my_dict = {}
    with open(filename, 'r') as json_file:
        # Read each line in the file
        for json_str in json_file:
            json_data = json.loads(json_str)
            id = json_data['id']
            lat = json_data['attributes']['lat']
            lng = json_data['attributes']['lng']
            if id in list(my_dict.keys()):
                loc_lst = my_dict[id]
                loc_lst.append((lat, lng))
                my_dict[id] = loc_lst
            else:
                loc_lst = [(lat, lng)]
                my_dict[id] = loc_lst
    return my_dict

def plot_tracks(gpx_track: [(float, float)], json_tracks_dict: dict, figure_name: str):
    fig = go.Figure()
    # add the gpx-track
    gpx_track = np.array(gpx_track)
    fig.add_trace(go.Scattermap(lat=gpx_track[:, 0], lon=gpx_track[:, 1], mode='markers+lines', name="Karina (GPS track smartphone)", showlegend=True, marker=dict(size=3), line=dict(width=5)))
    # add the json-tracks
    for id in list(json_tracks_dict.keys()):
        loc_lst = json_tracks_dict[id]
        loc_lst = np.array(loc_lst)
        if id =="01fe0709-028f-4d0b-b132-c8c34d833b42":
            fig.add_trace(go.Scattermap(lat=loc_lst[:, 0], lon=loc_lst[:, 1], mode='markers+lines', name="Karina (live track scooter API)", showlegend=True, line=dict(width=5)))
        else:
            fig.add_trace(go.Scattermap(lat=loc_lst[:, 0], lon=loc_lst[:, 1], mode='markers+lines', name="other user (live track scooter API)", showlegend=True, line=dict(width=5), visible="legendonly"))

    # add custom layout
    fig.update_layout(
        margin={'l': 0, 't': 30, 'b': 0, 'r': 0},
        map={'style': "open-street-map",
             'center': {'lat': gpx_track[0, 0], 'lon': gpx_track[0, 1]},
             'zoom': 15
             },
        title_text=figure_name,
    )
    fig.show()

if __name__ == "__main__":
    gpx_file = 'data/smartphoneGpsTrack.gpx'
    json_file = 'data/liveTrackScooterAPI.json'
    gpx_data = load_gpx_data(gpx_file)
    json_data = load_json_data(json_file)
    plot_tracks(gpx_data, json_data, figure_name="Comparison: Live Track Scooter API vs Smartphone GPS Track (Figure 2 in paper)")