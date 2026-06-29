#!/usr/bin/env python3

import laspy
import numpy as np
import open3d as o3d
import os
import json
import pyproj
import math

# --- Setup Paths ---
PCD_PATH = "/home/koneauto3/leo_rover_mapping_no_imu/outputs/rtabmap_cloud.pcd" 
JSON_PATH = "/home/koneauto3/leo_rover_mapping_no_imu/outputs/origin_metadata.json"
OUTPUT_LAS = "/home/koneauto3/leo_rover_mapping_no_imu/outputs/final_georef_map.las"

def convert():
    # 1. Load the metadata
    if not os.path.exists(JSON_PATH):
        print(f"CRITICAL ERROR: Metadata file not found at {JSON_PATH}")
        return
    
    with open(JSON_PATH, "r") as f:
        meta = json.load(f)
        off_x = meta["offset_easting"]   
        off_y = meta["offset_northing"]  
        off_z = meta["offset_altitude"]  
        epsg = meta.get("epsg", "3879")

    # 2. Load the original PCD
    if not os.path.exists(PCD_PATH):
        print(f"ERROR: Point cloud not found at {PCD_PATH}")
        return

    print(f"--- Processing: {os.path.basename(PCD_PATH)} ---")
    pcd = o3d.io.read_point_cloud(PCD_PATH)
    points = np.asarray(pcd.points)
    
    intensities = None
    if pcd.has_colors():
        intensities = np.asarray(pcd.colors)[:, 0] * 255 

    # 3. Setup LAS 1.4 Header
    header = laspy.LasHeader(point_format=3, version="1.4")
    crs = pyproj.CRS.from_user_input(epsg)
    header.add_crs(crs)    
    
    header.offsets = [off_x, off_y, off_z]
    header.scales = [0.001, 0.001, 0.001]
    las = laspy.LasData(header)
    
    # Isolate the original raw channels
    x_raw = points[:, 0]
    y_raw = points[:, 1]  
    z_raw = points[:, 2]

    # === STEP 1: YOUR PERFECT Y-AXIS TILT ===
    tilt_degrees = 35.0 
    theta = math.radians(tilt_degrees)
    
    print(f"Applying Leveling Tilt ({tilt_degrees}°)...")
    x_tilted = x_raw * math.cos(theta) + z_raw * math.sin(theta)
    z_tilted = -x_raw * math.sin(theta) + z_raw * math.cos(theta)
    y_tilted = y_raw  
    # ========================================

    # Map to the geographic axes (East, North, Up)
    east_base = y_tilted
    north_base = x_tilted
    up_base = z_tilted

    # === STEP 2: HEADING (YAW) CORRECTION ===
    # Positive values rotate Left (West). Negative values rotate Right (East).
    # Try a small number first, like 5.0 or 10.0 degrees!
    yaw_degrees = 20.0 
    phi = math.radians(yaw_degrees)

    print(f"Applying Heading/Yaw Rotation ({yaw_degrees}°)...")
    # 2D rotation on the flat ground plane
    east_final = east_base * math.cos(phi) - north_base * math.sin(phi)
    north_final = east_base * math.sin(phi) + north_base * math.cos(phi)
    up_final = up_base # Altitude is completely locked in
    # ========================================

    # === STEP 3: ALTITUDE (Z) CORRECTION ===
    # Standard GPS altitude is wildly inaccurate. 
    # Enter the manual offset here to snap the map to the true ground.
    z_correction = -25.3 # Change this to your exact measured difference
    print(f"Applying Altitude Correction: {z_correction} meters...")
    
    up_final = up_final + z_correction
    # ========================================

    # 4. Apply global geographic offsets
    las.x = east_final + off_x
    las.y = north_final + off_y
    las.z = up_final + off_z

    if intensities is not None:
        las.intensity = intensities.astype(np.uint16)

    # 5. Save the file
    print(f"Writing to: {OUTPUT_LAS}")
    las.write(OUTPUT_LAS)
    print("\n--- DONE ---")

if __name__ == "__main__":
    convert()