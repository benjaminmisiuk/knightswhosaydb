import numpy as np
import themachinethatgoesping as theping
import pandas as pd
from tqdm.auto import tqdm


def get_kmall_beam_data(ping, pn, back_mode="bs1"):
    c = ping.get_sensor_configuration()
    s = ping.get_sensor_data_latlon()
    s = theping.navigation.datastructures.SensordataUTM(s)

    north_m = s.northing
    east_m = s.easting

    g = c.compute_target_position("0", s)
    heading = g.yaw

    rows = []

    # There can be multiple MRZ datagrams per ping (dual swath mode)
    for mrz in ping.file_data.datagrams("#MRZ"):
        
        valid = np.where(mrz.soundings.get_detection_class_tensor() == 0)[0]

        if len(valid) == 0:
            continue

        xyz = mrz.soundings.get_xyz(valid)
        z = mrz.ping_info.get_z_water_level_re_ref_point_m()

        # Beam azimuth relative to vessel
        incidence_azimuth = np.degrees(np.arctan2(xyz.y, xyz.x)) % 360

        # Convert vessel-relative azimuth to world/geographic azimuth
        incidence_azimuth = (incidence_azimuth + heading) % 360

        # Transform XYZ into world coordinates
        xyz.rotate(heading)
        xyz.translate(z=-z)

        northing = xyz.x.astype(float) + north_m
        easting = xyz.y.astype(float) + east_m
        depth = xyz.z

        if back_mode == "bs1":
            bs = mrz.soundings.get_reflectivity_1_db_tensor()[valid]
        elif back_mode == "bs2":
            bs = mrz.soundings.get_reflectivity_2_db_tensor()[valid]
        else:
            raise ValueError(f"Unknown back_mode: {back_mode}")

        incidence_angle = (
            mrz.soundings.
            get_beam_incidence_angle_horizontal_plane_in_degrees_tensor()
            [valid])

        beam_angle = mrz.soundings.get_beam_angle_re_rx_deg_tensor()[valid]

        beam_numbers = valid
        ping_numbers = np.full(len(valid), pn)
        frequency = np.full(len(valid), mrz.ping_info.get_frequency_mode_hz())

        # to distinguish dual swath
        swath_index = np.full(len(valid), mrz.get_swath_along_position())

        rows.append(
            np.column_stack((
                ping_numbers,
                swath_index,
                beam_numbers,
                easting,
                northing,
                depth,
                bs,
                beam_angle,
                incidence_angle,
                incidence_azimuth,
                frequency,
            )))

    if not rows:
        return np.empty((0, 10))

    return np.concatenate(rows, axis=0)


def read_kmall(file, index, back_mode="bs1", verbose=False, **kwargs):
    fh = theping.echosounders.kmall.KMALLFileHandler(file,
                                                     index,
                                                     show_progress=verbose)
    pings = theping.pingprocessing.filter_pings.by_features(
        fh.get_pings(), ["bottom.xyz"])

    bs_data = []

    for pn, ping in enumerate(tqdm(pings, delay=10, desc=f"Reading {file}")):
        bs_data.append(get_kmall_beam_data(ping, pn, back_mode=back_mode))

    # numpy array
    return pd.DataFrame(
        np.concatenate(bs_data, axis=0),
        columns=[
            "ping_no",
            "swath_no",  # to distinguish dual swath
            "beam_no",
            "east",
            "north",
            "depth",
            "back",
            "beam_angle",
            "angle",
            "azimuth",
            "frequency",
        ],
    )
