import osmnx
import osmnx as ox
import sklearn  # yes, it is required for ox.distance
import matplotlib  # is required for ox.plot_graph(G)
import PyQt5  # is required for ox.plot_graph(G)

import matplotlib.pyplot as plt
import numpy as np

import pandas as pd
import geojson
import geopandas as gpd

ox.__version__



def single_trip_dist(dest_lng, dest_lat, start_lng, start_lat):
    place = "Kaiserslautern"
    G = ox.graph_from_place(place, network_type="bike")  # vs driving vs walk vs bike
    #ox.plot_graph(G)

    # get the nearest network nodes to two lat/lng points with the distance module
    orig = ox.distance.nearest_nodes(G, X=start_lat, Y=start_lng)
    dest = ox.distance.nearest_nodes(G, X=dest_lat, Y=dest_lng)

    # find the shortest path (by distance) between these nodes then plot it
    route = ox.shortest_path(G, orig, dest, weight="length")
    ox.plot_graph_route(G, route)


    # how long is our route in meters?
    edge_lengths = ox.routing.route_to_gdf(G, route)["length"]
    dist = round(sum(edge_lengths))
    if dist is None:
        return -1
    else:
        return dist


def many_trip_dist(location_paris_lst: []) -> [float]:
    # returns a list with distances in meters
    place = "Kaiserslautern"
    G = ox.graph_from_place(place, network_type="bike")  # vs driving vs walk vs bike
    #ox.plot_graph(G)
    dist_lst = []
    for pair in location_paris_lst:
        start_lat, start_lng, dest_lat, dest_lng  = pair

        # get the nearest network nodes to two lat/lng points with the distance module
        orig = ox.distance.nearest_nodes(G, Y=start_lat, X=start_lng)
        dest = ox.distance.nearest_nodes(G, Y=dest_lat, X=dest_lng)

        if orig == dest:
            dist_lst.append(0)
            continue

        # find the shortest path (by distance) between these nodes then plot it
        route = ox.shortest_path(G, orig, dest, weight="length")
        if route is None:
            dist_lst.append(-1)
            continue
        # how long is our route in meters?
        edge_lengths = ox.routing.route_to_gdf(G, route)["length"]
        dist = round(sum(abs(edge_lengths)))
        if dist is None:
            dist = -1
        dist_lst.append(dist)
    return dist_lst

#def store_model_offline():



if __name__ == '__main__':
    start_loc = (49.453739, 7.811148) # Monte Mare KL
    dest_loc = (49.425696, 7.750943)  # Parking house RPTU
    # google: 6,7 km vs osmx: 6,3 km
    my_restult = single_trip_dist(dest_loc[0], dest_loc[1], start_loc[0], start_loc[1])
    print(my_restult)
