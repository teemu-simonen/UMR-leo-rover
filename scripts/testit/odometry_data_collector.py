import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from pathlib import Path

class OdometryExporter(Node):
    def __init__(self):
        # Create ros2 node
        super().__init__("odometry_data_collector_node")
        self.get_logger().info("Odometry data collector node started")
        
        self.txt_output_path = Path("~/lidar/outputs/odometry.txt").expanduser()
        self.txt_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_saved_stamp = None
        self.min_time_between_samples = 0.2

        self.subscription = self.create_subscription(
            Odometry,
            "/aft_mapped_to_init",
            self.pose_callback,
            10
        )

        # Automatically clear/overwrite any old file on startup (NO header)
        with open(self.txt_output_path, "w", encoding="utf-8") as f:
            pass

    def pose_callback(self, msg):
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

        if self.last_saved_stamp is not None:
            if stamp - self.last_saved_stamp < self.min_time_between_samples:
                return
            
        self.last_saved_stamp = stamp

        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        
        # Write exactly 8 columns: stamp xpos ypos zpos xquat yquat zquat wquat
        with open(self.txt_output_path, "a", encoding="utf-8") as f:
            f.write(
                f"{stamp:.9f} {p.x:.6f} {p.y:.6f} {p.z:.6f} "
                f"{q.x:.6f} {q.y:.6f} {q.z:.6f} {q.w:.6f}\n"
            )

def main():
    rclpy.init()
    node = OdometryExporter()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

if __name__ == "__main__":
    main()