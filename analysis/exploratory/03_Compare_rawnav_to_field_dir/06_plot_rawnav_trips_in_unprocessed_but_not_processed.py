"""Plot field trips with issue."""
import pandas as pd
import os
import geopandas as gpd
import sys
path_working = (r"C:\Users\abibeka\OneDrive - Kittelson & Associates, Inc"
                r"\Documents\Github\WMATA_AVL")
sys.path.append(path_working)
import wmatarawnav as wr  # noqa E402
from helper_function_field_validation \
    import quick_and_dirty_schedule_qjump_mapping #noqa E402
path_source_data = (
    r"C:\Users\abibeka\OneDrive - Kittelson & Associates, Inc\Documents"
    r"\WMATA-AVL\Data\field_rawnav_dat")
path_processed_data = os.path.join(path_source_data, "processed_data")
path_processed_route_data = os.path.join(path_processed_data, "RouteData")
path_field_dir = (
    r'C:\Users\abibeka\OneDrive - Kittelson & Associates, Inc\Documents'
    r'\WMATA-AVL\Data\field_rawnav_dat')
path_wmata_schedule_data = (r"C:\Users\abibeka\OneDrive - "
                            r"Kittelson & Associates, Inc\Documents"
                            r"\WMATA-AVL\Data\wmata_schedule_data"
                            r"\Schedule_082719-201718.mdb")
# Globals
# Restrict number of zip files to parse to this number for testing.
# For all cases, use None
restrict_n = None
analysis_routes = [
    'S1', 'S2', 'S4', 'S9', '70', '79', '64',
    'G8', 'D32', 'H1', 'H2', 'H3', 'H4',
     'H8', 'W47']
analysis_days = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday',
    'Friday', 'Saturday', 'Sunday']
# EPSG code for WMATA-area work
wmata_crs = 2248
# 1. Read rawnav data. Subset trips that were observed in field and 
#  un-processed rawnav
# -----------------------------------------------------------------------------
# 1.1 All rawnav data
rawnav_dat = (
    wr.read_cleaned_rawnav(
        analysis_routes_=analysis_routes,
        analysis_days_=analysis_days,
        path = os.path.join(path_processed_data, "rawnav_data.parquet"))
    .drop(columns=['blank', 'lat_raw', 'long_raw', 'sat_cnt'])
                )
# 1.2 Summary--field data
path_validation_df = os.path.join(path_processed_data, "field_rawnav_dat.csv")
rawnav_field_summary_dat = (pd.read_csv(path_validation_df, index_col=0)
                            .query("has_data_from_rawnav_unprocessed == 1"))

temp = rawnav_dat.head()
# 1.3 Merge rawanv and Summary--field data (subset)
rawnav_qjump_dat = (
    rawnav_dat
    .merge(
        rawnav_field_summary_dat
        .drop(columns=["route", "pattern", "start_date_time"]),
        on=['filename', 'index_run_start'],
        how='right'
    )
)

del rawnav_dat

rawnav_qjump_gdf = (
    gpd.GeoDataFrame(
        rawnav_qjump_dat,
        geometry=gpd.points_from_xy(
            rawnav_qjump_dat.long, rawnav_qjump_dat.lat),
        crs='EPSG:4326')
    .to_crs(epsg=wmata_crs)
    )

rawnav_qjump_nm_map = {
    "georgia_columbia": "Georgia & Columbia",
    "georgia_piney_branch_long": "Georgia & Piney Branch",
    "georgia_piney_branch_shrt": "Georgia & Piney Branch",
    "georgia_irving": "Georgia & Irving",
    "sixteenth_u_shrt": "16th & U",
    "sixteenth_u_long": "16th & U",
    "eleventh_i_new_york": "11th & NY",
    "irving_fifteenth_sixteenth": "Irving & 16th",
}

# 2. Read qjump location and stop data
# -----------------------------------------------------------------------------
xwalk_seg_pattern_stop_in = wr.tribble(
    ['route', 'direction', 'seg_name_id', 'stop_id', "approx_time_qjump"],
    "79", "SOUTH", "georgia_columbia", 10981, 1500,
    "79", "SOUTH", "georgia_piney_branch_long", 4217, 900,
    "70", "SOUTH", "georgia_irving", 19186, 1500, # irving stop
    "70", "SOUTH", "georgia_columbia", 10981, 1500,  # columbia stop
    "70", "SOUTH", "georgia_piney_branch_shrt", 4217, 900,
    "S1", "NORTH", "sixteenth_u_shrt", 18042, 1500,
    "S2", "NORTH", "sixteenth_u_shrt", 18042, 1500,
    "S4", "NORTH", "sixteenth_u_shrt", 18042, 1500,
    "S9", "NORTH", "sixteenth_u_long", 18042, 1500,
    "64", "NORTH", "eleventh_i_new_york", 16490, 480,
    "G8", "EAST", "eleventh_i_new_york", 16490, 360,
    "D32", "EAST", "irving_fifteenth_sixteenth", 2368, 1200,
    "H1", "NORTH", "irving_fifteenth_sixteenth", 2368, 2500,
    "H2", "EAST", "irving_fifteenth_sixteenth", 2368, 1200,
    "H3", "EAST", "irving_fifteenth_sixteenth", 2368, 1200,
    "H4", "EAST", "irving_fifteenth_sixteenth", 2368, 1200,
    "H8", "EAST", "irving_fifteenth_sixteenth", 2368, 180,
    "W47", "EAST", "irving_fifteenth_sixteenth", 2368, 1200
)
xwalk_wmata_route_dir_pattern = (
    wr.read_sched_db_patterns(
        path=path_wmata_schedule_data,
        analysis_routes=analysis_routes)
    [['direction', 'route', 'pattern', 'stop_lon', 'stop_lat', 
      'stop_sort_order',
      'geo_description','stop_id']]
    .drop_duplicates()
)
xwalk_seg_pattern_stop = (
    xwalk_seg_pattern_stop_in
    .merge(xwalk_wmata_route_dir_pattern, on=['route', 'direction','stop_id'])
    .reindex(
        columns=[
            'route',
            'pattern',
            'direction',
            'stop_lon',
            'stop_lat',
            'seg_name_id',
            'stop_id',
            'stop_sort_order',
            'geo_description'
        ]
    )
    .assign(field_qjump_loc=(lambda df: df.seg_name_id.replace(
            rawnav_qjump_nm_map)))
)


xwalk_seg_pattern_stop_gdf = (
    gpd.GeoDataFrame(
        xwalk_seg_pattern_stop,
        geometry =
        gpd.points_from_xy(xwalk_seg_pattern_stop.stop_lon,
                           xwalk_seg_pattern_stop.stop_lat),
        crs='EPSG:4326')
    .to_crs(epsg=wmata_crs)
    )

# 3. Find nearest rawnav ping to qjump stop
# -----------------------------------------------------------------------------
xwalk_seg_pattern_stop_by_run_gdf_list = []
for i, row in rawnav_field_summary_dat.iterrows():
    xwalk_seg_pattern_stop_gdf_fil = xwalk_seg_pattern_stop_gdf.loc[
        lambda x:x.field_qjump_loc == row['field_qjump_loc']]
    rawnav_qjump_gdf_fil = rawnav_qjump_gdf.loc[
        lambda x: (x.filename == row['filename']) 
        & (x.index_run_start == row['index_run_start'])]
    xwalk_seg_pattern_stop_by_run_gdf_list.append(
        wr.merge_rawnav_target(
            target_dat=xwalk_seg_pattern_stop_gdf_fil,
            rawnav_dat=rawnav_qjump_gdf_fil)
        )
    
xwalk_seg_pattern_stop_by_run_gdf = \
    pd.concat(xwalk_seg_pattern_stop_by_run_gdf_list)
xwalk_seg_pattern_stop_by_run_gdf = \
    wr.make_target_rawnav_linestring(xwalk_seg_pattern_stop_by_run_gdf)


# 5. Output Debugging data
# -----------------------------------------------------------------------------
path_debug_dir = os.path.join(path_processed_data, "debug")


if not os.path.exists(path_debug_dir): os.makedirs(path_debug_dir)
rawnav_debug_file = os.path.join(path_debug_dir, 
                                 "rawnav_data_126_field_trips.csv")
rawnav_qjump_dat.to_csv(rawnav_debug_file, index=False)
# qjump stop--> rawnav--->without deletion
qjump_stop_file = os.path.join(path_debug_dir, 
                                 "qjump_stop_wo_deletion.csv")
pd.DataFrame(xwalk_seg_pattern_stop_by_run_gdf
 .drop(columns="geometry")).to_csv(qjump_stop_file)
# 6. Plot rawnav trajectory and nearest rawnav ping to qjump stop
# -----------------------------------------------------------------------------

    
group_rawnav_wmata_schedule = \
    xwalk_seg_pattern_stop_by_run_gdf.groupby(['field_qjump_loc',
                                               'filename', 'index_run_start'])
rawnav_groups = rawnav_qjump_dat.groupby(['field_qjump_loc',
                                               'filename', 'index_run_start'])
for name, rawnav_grp in rawnav_groups:
    route = rawnav_grp["route"].values[0]
    pattern = rawnav_grp["pattern"].values[0]
    has_processed_dat = \
        rawnav_grp["has_data_from_rawnav_processed"].values[0]
    relevant_rawnav_wmata_schedule_dat = \
        group_rawnav_wmata_schedule.get_group(name)
    save_file = (f"{has_processed_dat}_{name[0]}_{route}_"
                f"{pattern}__{name[1]}_{name[2]}.html")
    save_dir_1 = os.path.join(path_processed_data, "trajectory_figures")
    if not os.path.exists(save_dir_1): os.makedirs(save_dir_1)
    map1 = wr.plot_rawnav_trajectory_with_wmata_schedule_stops(
        rawnav_grp, relevant_rawnav_wmata_schedule_dat)
    save_dir_1 = os.path.join(path_processed_data, "TrajectoryFigures")
    map1.save(os.path.join(save_dir_1, f"{save_file}"))




