import numpy as np
import themachinethatgoesping as theping
import pandas as pd
from tqdm.auto import tqdm


def get_kongsbergall_beam_data(ping, pn, back_mode="bs1"):
    
    c = ping.get_sensor_configuration()
    s = ping.get_sensor_data_latlon()
    s = theping.navigation.datastructures.SensordataUTM(s)
    
    north_m = s.northing
    east_m = s.easting
    
    g = c.compute_target_position("0", s)
    heading = g.yaw
    
    rows = []
    
    drra = ping.file_data.datagrams('RawRangeAndAngle')[0]
    dxyz = ping.file_data.datagrams('XYZDatagram')[0]
    rp = ping.file_data.get_runtime_parameters()
    
    valid = np.where(dxyz.beams.get_detection_is_valid_tensor() == 1)[0]
    
    # if len(valid) == 0:
    #     continue
    
    xyz = dxyz.beams.get_xyz(valid)
    z = dxyz.get_transmit_transducer_depth()
    
    # Beam azimuth relative to vessel
    # simplified
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
        bs = dxyz.beams.get_backscatter_tensor()[valid]
    else:
        raise ValueError(f"Unknown back_mode: {back_mode}")
    
    incidence_angle = (
        dxyz.beams.get_beam_incidence_angle_horizontal_plane_in_degrees_tensor()
        [valid]
    )
    
    beam_angle = drra.beams.get_beam_crosstrack_angle_in_degrees_tensor()[valid]
    
    beam_numbers = valid
    ping_numbers = np.full(len(valid), pn)
    frequency = np.full(len(valid), rp.get_frequency_mode_in_hertz())
    
    # # to distinguish dual swath
    # old.all does not include swath number, we'd have to guess this 
    #swath_index = np.full(len(valid), mrz.get_swath_along_position())
    
    return np.column_stack((
        ping_numbers,
        #swath_index,
        beam_numbers,
        easting,
        northing,
        depth,
        bs,
        beam_angle,
        incidence_angle,
        incidence_azimuth,
        frequency,
    ))


def read_kongsbergall(file, index, back_mode="bs1", verbose=False, **kwargs):
    fh = theping.echosounders.kongsbergall.KongsbergAllFileHandler(file,
                                                     index,
                                                     show_progress=verbose)
    pings = theping.pingprocessing.filter_pings.by_features(
        fh.get_pings(), ["bottom.xyz"])

    bs_data = []

    for pn, ping in enumerate(tqdm(pings, delay=10, desc=f"Reading {file}")):
        bs_data.append(get_kongsbergall_beam_data(ping, pn, back_mode=back_mode))

    # numpy array
    return pd.DataFrame(
        np.concatenate(bs_data, axis=0),
        columns=[
            "ping_no",
            #"swath_no",  # not yet computed
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
