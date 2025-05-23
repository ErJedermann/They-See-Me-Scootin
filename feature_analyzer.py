import math
import numpy as np
import plots

def __ratio_of_two_freatures(scooter_actions_dict: dict, feature_a: str, feature_b: str) -> dict:
    # calculates the factor (ratio) of feature_a / feature_b
    result_dict = {}
    for action_type in list(scooter_actions_dict.keys()):
        full_feature_dict_lst = scooter_actions_dict[action_type]
        factor_lst = []
        for temp_feature_dict in full_feature_dict_lst:
            value_b = temp_feature_dict[feature_b]
            if value_b == 0:  # avoid a divide by zero error
                continue
            value_a = temp_feature_dict[feature_a]
            factor = value_a / value_b
            factor_lst.append(factor)
        result_dict[action_type] = factor_lst
    return result_dict

def __plot_some_data(data_sets: dict[str, list[dict]], x_axis: str, y_axis: str, z_axis: str):
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



def analyze_features(scooter_actions_dict: dict[str, list[dict]]):
    # input: scooter_actions_dict: a dict with all classified scooter-actions. each scooter-action has a list of feature-dicts
    # 1: the factor between beeline_distance and street_distance. In thesis avg = 1.32, but I want more details
    data_dict1 = __ratio_of_two_freatures(scooter_actions_dict, feature_a="street_dist", feature_b="beeline_dist")
    plots.plot_features_selfmade_quantiles(data_lst_dict=data_dict1, y_label="factor", figure_name="factor of street_dist/beeline_dist")
    # 2: factor between street_disctance and range_meter_delta
    data_dict2 = __ratio_of_two_freatures(scooter_actions_dict, feature_a="street_dist", feature_b="range_meter_delta")
    plots.plot_features_selfmade_quantiles(data_lst_dict=data_dict2, y_label="factor", figure_name="factor of street_dist/range_meter_delta")
    # 3: factor between range_meter_delta and battery_change
    data_dict3 = __ratio_of_two_freatures(scooter_actions_dict, feature_a="range_meter_delta", feature_b="battery_change")
    plots.plot_features_selfmade_quantiles(data_lst_dict=data_dict3, y_label="factor", figure_name="factor of range_meter_delta/battery_change")


def analyze_loadings(loadings_lst):
    my_plot_dict_lst = []
    for feature_dict in loadings_lst:
        temp_dict = {}
        temp_dict['battery_change'] = feature_dict['battery_change']  # [%]
        old_state = feature_dict['dataset_old']
        new_state = feature_dict['dataset_new']
        temp_dict['battery_old'] = old_state['batteryLevel']
        temp_dict['battery_new'] = new_state['batteryLevel']
        temp_dict['duration'] = feature_dict['duration'] /60  # minutes
        temp_dict['beeline_dist'] = feature_dict['beeline_dist']
        my_plot_dict_lst.append(temp_dict)
    foo = {'loading specials': my_plot_dict_lst}
    __plot_some_data(data_sets=foo, x_axis='battery_change', y_axis='duration', z_axis='beeline_dist')
    __plot_some_data(data_sets=foo, x_axis='duration', y_axis='battery_old', z_axis='battery_new')
