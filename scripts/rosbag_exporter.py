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
        self.get_logger().info("Unified Data Exporter Started. Zero-Origin Mode Active.")
        
        # --- Setup Paths ---
        self.base_dir = Path("~/lidar/outputs").expanduser()
        self.gps_dir = self.base_dir / "gps_dir"
        self.odom_path = self.base_dir / "odometry.txt"

        if self.gps_dir.exists():
            shutil.rmtree(self.gps_dir)
        self.gps_dir.mkdir(parents=True, exist_ok=True)

        with open(self.odom_path, "w", encoding="utf-8") as f:
            pass

        # --- Setup Variables ---
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3879", always_xy=True)
        self.odom_buffer = []  
        self.gps_history = []  
        self.last_odom_stamp = None
        self.min_time_between_odom = 0.2
        
        # NEW: Variables to store our local origin
        self.origin_x = None
        self.origin_y = None
        self.origin_z = None

        # --- Subscribers ---
        self.gps_sub = self.create_subscription(NavSatFix, "/fix", self.gps_callback, 10)
        self.odom_sub = self.create_subscription(Odometry, "/aft_mapped_to_init", self.odom_callback, 10)

    def odom_callback(self, msg):
        if len(self.gps_history) < 2:
            return 
            
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if stamp < self.gps_history[1]:
            return

        if self.last_odom_stamp is not None:
            if stamp - self.last_odom_stamp < self.min_time_between_odom:
                return
        self.last_odom_stamp = stamp

        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        
        line = f"{stamp:.9f} {p.x:.6f} {p.y:.6f} {p.z:.6f} {q.x:.6f} {q.y:.6f} {q.z:.6f} {q.w:.6f}\n"
        self.odom_buffer.append((stamp, line))

    def gps_callback(self, msg):
            sec = msg.header.stamp.sec
            nano = msg.header.stamp.nanosec
            gps_stamp = sec + nano * 1e-9
            self.gps_history.append(gps_stamp)

            # Process GPS data
            raw_x, raw_y = self.transformer.transform(msg.longitude, msg.latitude)
            raw_z = msg.altitude
            std_x = 5.0
            std_y = 5.0
            std_z = 15.0

            # std_x = math.sqrt(abs(msg.position_covariance[0]))
            # std_y = math.sqrt(abs(msg.position_covariance[4]))
            # std_z = math.sqrt(abs(msg.position_covariance[8]))

            # --- ZERO-ORIGIN LOGIC ---
            if self.origin_x is None:
                self.origin_x, self.origin_y, self.origin_z = raw_x, raw_y, raw_z
                self.get_logger().info(f"Origin locked at: {raw_x:.2f}, {raw_y:.2f}, {raw_z:.2f}")

            # Subtract the origin to prevent floating-point collapse!
            x = raw_x - self.origin_x
            y = raw_y - self.origin_y
            z = raw_z - self.origin_z

            filename = f"{sec}_{nano}.txt"
            filepath = self.gps_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"{gps_stamp:.9f} {x:.3f} {y:.3f} {z:.3f} {std_x:.3f} {std_y:.3f} {std_z:.3f}\n")

            # --- THE FIX: Bracketing the End ---
            # We wait until we have 3 GPS points, and then only write Odometry up to the PREVIOUS one.
            # This guarantees the newest GPS point is always waiting in the future!
            if len(self.gps_history) >= 3:
                safe_start_time = self.gps_history[1]
                safe_end_time = self.gps_history[-2] # The PREVIOUS GPS ping
                
                with open(self.odom_path, "a", encoding="utf-8") as f:
                    for odom_time, line in self.odom_buffer:
                        if safe_start_time <= odom_time <= safe_end_time:
                            f.write(line)
                
                # Clear frames older than the safe_end_time
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