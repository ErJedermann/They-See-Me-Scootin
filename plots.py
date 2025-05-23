import math
import numpy as np
import plotly.graph_objects as go


def __get_percentile(data, p: float):
    """
    Calculates quartiles as written in the plotly documentation: https://plotly.com/python/box-plots/#choosing-the-algorithm-for-computing-quartiles.
    Modification: Remove the +0.5 to avoid out of bounce for small datasets.
    :param data: The data to find the percentile.
    :param p: The percentile that should be found. Range [0.0, 1.0]. Examples: 0.25=25th percentile, 0.5=50th percentile.
    :return: The value of the requested percentile.
    """
    data.sort()
    n = len(data)
    x = n * p# + 0.5
    x1, x2 = math.floor(x), math.ceil(x)
    if x1 == x2:
        return data[x1 - 1]
    y1, y2 = data[x1 - 1], data[x2 - 1]  # account for zero-indexing
    return y1 + ((x - x1) / (x2 - x1)) * (y2 - y1)



def plot_3D_data_dict(data_points_3D_dict: dict[str, list[(float, float, float)]],
                      x_label: str, y_label: str, z_label: str, figure_name: str):
    # data_points_3D_dict: {'data_set1_name': [(x0, y0, z0), (x1, y1, z1),...]; 'data_set2_name': [...]}
    fig = go.Figure()
    for data_name in list(data_points_3D_dict.keys()):
        data_lst = data_points_3D_dict[data_name]
        data_lst = np.array(data_lst)
        fig.add_trace(go.Scatter3d(x=data_lst[:, 0], y=data_lst[:, 1], z=data_lst[:, 2], mode='markers', name=data_name))
    # add custom layout
    fig.update_layout(
        title_text=figure_name,
        width=1500,
        height=1000,
        # showlegend=False,
        scene=dict(aspectmode='cube',  # data, cube, auto, manual
                   xaxis_title=x_label,
                   yaxis_title=y_label,
                   zaxis_title=z_label),
        # scene=dict(xaxis=noaxis, yaxis=noaxis, zaxis=noaxis, aspectmode='data'),
    )
    fig.show()


def plot_features_selfmade_quantiles(data_lst_dict: dict[str, list[float]], y_label: str, figure_name: str = None):
    # atk_types_data = {atk_type: [[x1], [x2], ...] }
    if figure_name is None:
        figure_name = f"some data"
    fig = go.Figure()
    data_types = list(data_lst_dict.keys())
    for temp_type in data_types:
        temp_data = data_lst_dict[temp_type]
        temp_arr = np.array(temp_data)
        low_fences = np.array(__get_percentile(temp_arr, 0.01))
        q1_list = np.array(__get_percentile(temp_arr, 0.1))
        q2_list = np.array(__get_percentile(temp_arr, 0.5))
        q3_list = np.array(__get_percentile(temp_arr, 0.9))
        upper_fences = np.array(__get_percentile(temp_arr, 0.99))
        new_trace = go.Box(name=temp_type,
                           lowerfence=low_fences,
                           q1=q1_list,
                           median=q2_list,
                           q3=q3_list,
                           upperfence=upper_fences,
                           )
        fig.add_trace(new_trace)


    # add custom layout
    fig.update_layout(
        title_text=figure_name,
        width=950,
        height=500,
        yaxis_title=y_label,
        # yaxis_title="region of interest [km²]",
        # yaxis_range=[-2.2, 6.2],  # original for 4h iridium-figure of the paper
        # yaxis_range=[-1.8, 3.5],  # for the starlink figure in the paper
        boxmode='group',  # group together boxes of the different traces for each value of x
        # font=dict(
        #     size=16,
        # )
    )
    #fig.update_yaxes(type="log")
    fig.show()

if __name__ == '__main__':
    test_dict1 = {'type1': list(np.random.rand(5,3)),
                 'type2': list(np.random.rand(6,3)+np.array([1, 1.5, 0.5]))}
    #plot_3D_data_dict(data_points_3D_dict=test_dict1, x_label="x", y_label="y", z_label="z", figure_name="figure")
    test_dict2 = {'type1': list(np.random.random(100)+0.2),
                  'type2': list(np.random.random(100)*1.2+0.1)}
    plot_features_selfmade_quantiles(test_dict2, y_label="values")
