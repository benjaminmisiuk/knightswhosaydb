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

supported_models = [
    "em2040", 
    "em710", 
    "em302", 
    "em122", 
    "em712", 
    "em304", 
    "em124", 
    "me70bo", 
    ]  # example supported models

def remove_trailing_letters(model):
    import re
    return re.sub(r'\D+$', '', model)

def catch_fh_problems(fh):
    
    error = ""
        
    # check for valid model numbers
    for nav_key in fh.navigation_interface.get_navigation_interpolator_keys():
        nav = fh.navigation_interface.get_navigation_interpolator(nav_key)
        sc = nav.get_sensor_configuration()
        model = sc.get_model_name()

        error = ""
        
        if not remove_trailing_letters(model.lower()) in supported_models:
            if model.lower() == "me70bo":
                continue
            
            # We only create a warning for unsupported models, not an error
            # Errors will happen later in case no XYZ pings are found
            error = f"Unsupported EM model: {model} that did not generate XYZ data.\nCurrently supported models are: {supported_models}.\nSupport for this model will be added in the future.\n"
            import sys
            print(f"\n{error}",
                  file=sys.stderr)

    return error


def read_kongsbergall(file, index, back_mode="bs1", verbose=False, **kwargs):
    fh = theping.echosounders.kongsbergall.KongsbergAllFileHandler(file,
                                                     index,
                                                     show_progress=verbose)
    pings = theping.pingprocessing.filter_pings.by_features(
        fh.get_pings(), ["bottom.xyz"])

    # catch potential problems with the file handler before processing pings
    error_ = catch_fh_problems(fh)

    # check if there are no XYZ pings
    if len(pings) == 0:
        error = f"\nNo XYZ pings found in file: {file}"
        if file.endswith(".wcd"):
            error += "\nPotential cause: File ends with .wcd which indicates you might supplied water column files instead of the bottom tracking related .all files"
        if len(error_) > 0:
            error += "\nPotential cause: " + error_
        raise ValueError(error)
    
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
