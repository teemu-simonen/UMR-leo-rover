import laspy
import numpy as np
import open3d as o3d
import os
import json
import pyproj
import math

# --- HARDCODED FILEPATHS ---
PCD_PATH = "/home/koneauto3/lidar/ros2_dev/src/point_lio_ros2/PCD/georef_scans.pcd"
JSON_PATH = "/home/koneauto3/lidar/outputs/origin_metadata.json"
OUTPUT_LAZ = "/home/koneauto3/lidar/final_georef_map.laz"

def convert():
    if not os.path.exists(JSON_PATH):
        print(f"CRITICAL ERROR: Metadata file not found at {JSON_PATH}")
        return
    
    with open(JSON_PATH, "r") as f:
        meta = json.load(f)
        off_x = meta["offset_easting"]   
        off_y = meta["offset_northing"]  
        off_z = meta["offset_altitude"]  
        epsg = meta.get("epsg", "3879")

    if not os.path.exists(PCD_PATH):
        print(f"ERROR: Point cloud not found at {PCD_PATH}")
        return

    print(f"--- Processing: {os.path.basename(PCD_PATH)} ---")
    pcd = o3d.io.read_point_cloud(PCD_PATH)
    points = np.asarray(pcd.points)
    
    intensities = None
    if pcd.has_colors():
        intensities = np.asarray(pcd.colors)[:, 0] * 255 

    # --- CENTER-PIVOT ROTATION ---
    YAW_DEG = 0.0  # Modify Rotation
    
    # 1. Find the center of the building
    center = np.mean(points[:, :2], axis=0)
    
    # 2. Move to 0,0 temporarily
    shifted_pts = points[:, :2] - center 
    
    # 3. Apply the 90-degree spin
    rad = math.radians(YAW_DEG)
    cos_v = math.cos(rad)
    sin_v = math.sin(rad)
    rot_matrix = np.array([[cos_v, -sin_v], [sin_v, cos_v]])
    rotated_pts = np.dot(shifted_pts, rot_matrix.T) + center
    
    # 4. Save the spun points back to the array
    points[:, 0] = rotated_pts[:, 0]
    points[:, 1] = rotated_pts[:, 1]

    # --- SETUP LAZ HEADER ---
    header = laspy.LasHeader(point_format=3, version="1.4")
    crs = pyproj.CRS.from_user_input(epsg)
    header.add_crs(crs)
    
    header.offsets = [off_x, off_y, off_z]
    header.scales = [0.001, 0.001, 0.001] # (Using 0.001 based on your last working script)

    # --- ASSIGN COORDINATES (STANDARD MAPPING) ---
    las = laspy.LasData(header)
    
    # Notice X goes to X, Y goes to Y. The rotation is already done!
    las.x = points[:, 0] + off_x
    las.y = points[:, 1] + off_y
    las.z = points[:, 2] + off_z

    if intensities is not None:
        las.intensity = intensities.astype(np.uint16)

    # --- SAVE FILE ---
    print(f"Writing to: {OUTPUT_LAZ}")
    las.write(OUTPUT_LAZ)
    print("\n--- DONE ---")

if __name__ == "__main__":
    convert()