import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from nav_msgs.msg import Odometry
from pyproj import Transformer
from pathlib import Path
import math
import shutil

class UnifiedExporter(Node):
    def __init__(self):
        super().__init__("unified_exporter_node")
        self.get_logger().info("Unified Data Exporter Started. Full Georeferencing Hacks Active.")
        
        # --- Setup Paths ---
        self.base_dir = Path("~/lidar/outputs").expanduser()
        self.gps_dir = self.base_dir / "gps_dir"
        self.odom_path = self.base_dir / "odometry.txt"

        # Clean old data to prevent ghosting
        if self.gps_dir.exists():
            shutil.rmtree(self.gps_dir)
        self.gps_dir.mkdir(parents=True, exist_ok=True)

        with open(self.odom_path, "w", encoding="utf-8") as f:
            pass

        # --- Setup Variables ---
        # EPSG:3879 is ETRS89 / GK25FIN (Metric local grid for Finland)
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3879", always_xy=True)
        
        self.odom_buffer = []  
        self.gps_history = []  
        self.last_odom_stamp = None
        self.min_time_between_odom = 0.2 # Roughly 5Hz Odometry downsampling
        
        # Origin Variables for Local Translation
        self.origin_x = None
        self.origin_y = None
        self.origin_z = None

        # Variables for the "Z-Stealer" and "Distance Anchor"
        self.current_odom_x = 0.0
        self.current_odom_y = 0.0
        self.current_odom_z = 0.0

        # --- Subscribers ---
        self.gps_sub = self.create_subscription(NavSatFix, "/fix", self.gps_callback, 10)
        self.odom_sub = self.create_subscription(Odometry, "/aft_mapped_to_init", self.odom_callback, 10)

    def odom_callback(self, msg):
        # 1. Update our current high-precision LiDAR location tracking
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        
        self.current_odom_x = p.x
        self.current_odom_y = p.y
        self.current_odom_z = p.z  # Used to fix the "Taffy/Bouncing" effect

        # 2. Buffer the odometry for the Bracketing Logic
        if len(self.gps_history) < 2:
            return 
            
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if stamp < self.gps_history[1]:
            return

        if self.last_odom_stamp is not None:
            if stamp - self.last_odom_stamp < self.min_time_between_odom:
                return
        self.last_odom_stamp = stamp
        
        # KITTI Format string
        line = f"{stamp:.9f} {p.x:.6f} {p.y:.6f} {p.z:.6f} {q.x:.6f} {q.y:.6f} {q.z:.6f} {q.w:.6f}\n"
        self.odom_buffer.append((stamp, line))

    def gps_callback(self, msg):
        sec = msg.header.stamp.sec
        nano = msg.header.stamp.nanosec
        gps_stamp = sec + nano * 1e-9
        self.gps_history.append(gps_stamp)

        # 1. Process Raw GPS data into EPSG:3879 Meters
        raw_x, raw_y = self.transformer.transform(msg.longitude, msg.latitude)
        
        # Hardcode realistic RUTX11 errors to prevent algorithm panic
        std_x = 5.0
        std_y = 5.0
        std_z = 15.0

        # 2. Lock the Origin on the first ping
        if self.origin_x is None:
            self.origin_x = raw_x
            self.origin_y = raw_y
            self.origin_z = msg.altitude
            self.get_logger().info(f"Origin locked at: {raw_x:.2f}, {raw_y:.2f} (EPSG:3879)")

        # 3. Get the local translation (to prevent 32-bit float point cloud collapse)
        raw_x_local = raw_x - self.origin_x
        raw_y_local = raw_y - self.origin_y

        # --- THE DISTANCE ANCHOR (Fixes "The Smear" / Scale Factor) ---
        # Calculate true distance traveled vs noisy GPS distance
        odom_dist = math.hypot(self.current_odom_x, self.current_odom_y)
        gps_dist = math.hypot(raw_x_local, raw_y_local)

        # Force the GPS point to perfectly match the LiDAR distance from the origin,
        # but keep its true geographical heading!
        if gps_dist > 0.5:  
            scale_correction = odom_dist / gps_dist
            x = raw_x_local * scale_correction
            y = raw_y_local * scale_correction
        else:
            x = raw_x_local
            y = raw_y_local

        # --- THE Z-STEALER (Fixes "The Taffy" / Altitude Bouncing) ---
        z = self.current_odom_z

        # 4. Write to File
        # NOTE: Timestamp removed from string to fix FlexCloud parsing bug ("The Pancake")
        filename = f"{sec}_{nano}.txt"
        filepath = self.gps_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"{x:.3f} {y:.3f} {z:.3f} {std_x:.3f} {std_y:.3f} {std_z:.3f}\n")

        # 5. --- THE BRACKETING LOGIC ---
        # Guarantees SLAM odometry never exceeds the bounds of the 1Hz GPS pings
        if len(self.gps_history) >= 3:
            safe_start_time = self.gps_history[1]
            safe_end_time = self.gps_history[-2] 
            
            with open(self.odom_path, "a", encoding="utf-8") as f:
                for odom_time, line in self.odom_buffer:
                    if safe_start_time <= odom_time <= safe_end_time:
                        f.write(line)
            
            # Clear printed frames from buffer
            self.odom_buffer = [(t, l) for t, l in self.odom_buffer if t > safe_end_time]

def main():
    rclpy.init()
    node = UnifiedExporter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

if __name__ == "__main__":
    main()