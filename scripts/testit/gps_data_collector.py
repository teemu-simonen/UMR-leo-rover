import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from pyproj import Transformer
from pathlib import Path
import math
import shutil

# Create gps_exporter ros2 node
class GPSLiveExporter(Node):
    def __init__(self):
        super().__init__("gps_exporter")
        self.get_logger().info("GPS exporter node started")

        # Transform EPSG:4326 coordinates to EPSG:3879
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3879", always_xy=True)
        
        # Subscribe to /fix ros2 topic provided by rutx11 gps
        self.subscription = self.create_subscription(
            NavSatFix,
            "/fix",
            self.fix_callback,
            10
        )
        
        # FlexCloud requires a DIRECTORY of files, not a single file
        self.gps_dir = Path("~/lidar/outputs/gps_dir").expanduser()
        
        # Safety wipe: Delete the folder if it exists to clear old rosbag data, then recreate it
        if self.gps_dir.exists():
            shutil.rmtree(self.gps_dir)
        self.gps_dir.mkdir(parents=True, exist_ok=True)
        
        self.get_logger().info(f"Saving individual GPS files to: {self.gps_dir}")

    # Receives values taken from /fix ros2 topic and writes them to individual .txt files
    def fix_callback(self, msg):
        sec = msg.header.stamp.sec
        nano = msg.header.stamp.nanosec
        stamp = sec + nano * 1e-9
        
        x, y = self.transformer.transform(msg.longitude, msg.latitude)
        std_x = math.sqrt(abs(msg.position_covariance[0]))
        std_y = math.sqrt(abs(msg.position_covariance[4]))
        std_z = math.sqrt(abs(msg.position_covariance[8]))

        # Create the unique filename according to FlexCloud format: sec_nanosec.txt
        filename = f"{sec}_{nano}.txt"
        filepath = self.gps_dir / filename

        # Write the 7 required columns: stamp x y altitude std_x std_y std_z
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(
                f"{stamp:.9f} {x:.3f} {y:.3f} {msg.altitude:.3f} "
                f"{std_x:.3f} {std_y:.3f} {std_z:.3f}\n"
            )

def main():
    rclpy.init()
    node = GPSLiveExporter()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

if __name__ == "__main__":
    main()