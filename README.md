# They See Me Scooting

This repository belongs to the paper *They See Me Scooting — A Long-Term Real-World Data Analysis of Shared Micro-Mobility Services and their Privacy Leakage* from Karina Elzer, Eric Jedermann, Stefanie Roos and Jens Schmitt. 
The paper can be found online at TODO (will be published in July 2025 at Euro SnP).

When using this code, please cite the paper.

## Installation

1. Inatall python 3.11 viraual environment:

   $ `python3.11 -m venv ./venv/`

2. Activate it:

   $ `source venv/bin/activate`

3. Install the requirements:

   $ `pip install -r requirements.txt`

## Run the algorithm to identify trips without using static IDs

1. Run the script to execute the algorithm for the first evaluation day (Oct 1st 2023):

   $ `python find_scooters_without_IDs_paper.py`

2. To change the evaluation day, change the list index in row 334 of file *find_scooters_without_IDs_paper.py*.

   `used_date = dates_lst[0]` -> `used_date = dates_lst[i]` with `i` in [0 - 6].

   Then run the script again.

3. When evaluating the algorithm for all seven days, Table 8 from the Paper is the result.

## Most important files:

- *live_gps_comparator.py*: Makes Figure 2 from the paper. Execute with the command: 

   $ `python live_gps_comparator.py`

- *find_scooters_without_IDs_paper.py*: Makes the evaluation, from section 6 in the paper. Execute with the command:

   $ `python find_scooters_without_IDs_paper.py`

## All files and their purpose:

- *dataloader.py*: Provides functions to load the scooter-data from json-files.

- *evaluation.py*: Contains the methods to evaluate the quelity of the trip estimation.

- *feature_analyzer.py*: Provides the analysis and visualization methods.

- *find_scooters_without_IDs_paper.py*: The main-script that performs the trip identification without using the scooter-ID.

- *live_gps_comparator.py*: Makes Figure 2 from the paper. It compares tracks of a test ride. One track is a smartphone recorded GPS track, the second is a live track from the scooter vendors API.

- *pathfinder.py*: Provides methods to find the shortest path between two locations, based on OpenStreetMap routing.

- *plots.py*: Provides methods to create plots.

- *trip_extractor_full_data.py*: Provides the method *identify_trips_full_data* to identify all trips (uses the full data set including IDs). This method provides the ground truth. Also provides some nice graphics to see relations between features.

- *utilities.py*: Some utility functions


















