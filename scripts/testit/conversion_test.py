from pathlib import Path
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
from pyproj import Transformer

bag_path = Path("~/lidar/rosbags/rosbag_etupiha_smooth_1").expanduser()
txt_output_path = Path("~/lidar/outputs/gps_coordinates_3879.txt").expanduser()

reader = SequentialReader()

storage_options = StorageOptions(
    uri=str(bag_path),
    storage_id="sqlite3"
)

converter_options = ConverterOptions(
    input_serialization_format="cdr",
    output_serialization_format="cdr"
)

reader.open(storage_options, converter_options)

topic_types = reader.get_all_topics_and_types()
type_map = {topic.name: topic.type for topic in topic_types}
fix_type = get_message(type_map["/fix"])
transformer = Transformer.from_crs("EPSG:4326", "EPSG:3879", always_xy=True)

txt_output_path.parent.mkdir(parents=True, exist_ok=True)




print("Bag path is:")
print(bag_path)
print("Exists:", bag_path.exists())


print("Topics in the bag:")
for topic in topic_types:
    print(f"{topic.name} -> {topic.type}")

count = 0

with open(txt_output_path, "w", encoding="utf-8") as f:
    f.write("# stamp x_3879 y_3879 altitude latitude longitude"f"\n")
    
    while reader.has_next():
        topic, data, t = reader.read_next()

        if topic == "/fix":
            msg = deserialize_message(data, fix_type)
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            x, y = transformer.transform(msg.longitude, msg.latitude)

            f.write(
                f"{stamp:.9f} "
                f"{x:.3f} {y:.3f} {msg.altitude:.3f} "
                f"{msg.latitude:.8f} {msg.longitude:.8f}\n"
            )

            count += 1
            if count == 5:
                break