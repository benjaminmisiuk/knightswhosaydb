import numpy as np
import themachinethatgoesping as theping
import pandas as pd
from tqdm.auto import tqdm


def read_kmall(file, index, back_mode = 'bs1', verbose=False, **kwargs):
    fh = theping.echosounders.kmall.KMALLFileHandler(file, index, show_progress=verbose)
    pings = theping.pingprocessing.filter_pings.by_features(fh.get_pings(), ['bottom.xyz'])
    northing, easting, depth, bs, beam_angle, beam_numbers, ping_numbers, incidence_angle, frequency = [], [], [], [], [], [], [], [], []
    for pn, ping in enumerate(tqdm(pings, delay=10, desc=f"Reading {file}")):
        c = ping.get_sensor_configuration()
        s = ping.get_sensor_data_latlon()
        s = theping.navigation.datastructures.SensordataUTM(s)
        north_m = s.northing
        east_m = s.easting

        g = c.compute_target_position('0', s)
        heading = g.yaw

        # mrz datagram (for now necessary)
        mrz = ping.file_data.datagrams('#MRZ')[0]

        # valid detections
        valid = np.where(mrz.soundings.get_detection_class_tensor() == 0)[0]

        # xyz relative to source
        xyz = mrz.soundings.get_xyz(valid)
        z = mrz.ping_info.get_z_water_level_re_ref_point_m()

        # compute xyz in utm
        xyz.rotate(heading)
        xyz.translate(z=-z)

        # assemble data
        if back_mode == 'bs1':
            bs.append(mrz.soundings.get_reflectivity_1_db_tensor()[valid])
        elif back_mode == 'bs2':
            bs.append(mrz.soundings.get_reflectivity_2_db_tensor()[valid])

        northing.append(xyz.x.astype(float) + north_m)
        easting.append(xyz.y.astype(float) + east_m)
        depth.append(xyz.z)
        incidence_angle.append(mrz.soundings.get_beam_incidence_angle_horizontal_plane_in_degrees_tensor()[valid])
        beam_angle.append(mrz.soundings.get_beam_angle_re_rx_deg_tensor()[valid])
        beam_numbers.append(valid)
        ping_numbers.append(np.repeat(pn, len(xyz.z)))
        frequency.append(np.repeat(mrz.ping_info.get_frequency_mode_hz(), len(xyz.z))) #.all has no frequency mode

    #numpy array
    bs_data = np.column_stack(
        (
            np.concatenate(easting),
            np.concatenate(northing),
            np.concatenate(depth),
            np.concatenate(bs),
            np.concatenate(beam_angle),
            np.concatenate(ping_numbers),
            np.concatenate(incidence_angle),
            np.concatenate(frequency)
        )
    )

    return(
        pd.DataFrame(bs_data, columns=['east', 'north', 'depth', 'back', 'beam_angle', 'ping_no', 'angle', 'frequency'])
    )