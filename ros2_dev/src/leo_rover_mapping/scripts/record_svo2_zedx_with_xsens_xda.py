import sys
import cv2
import pyzed.sl as sl
import argparse
import threading
import time
import serial  # Fallback serial
import struct  # For packing custom data
import xsensdeviceapi.xsensdeviceapi_py38_64 as xda  # Xsens Device API (adjust version/path if needed)

# Global flags and shared objects
external_data_recording = False
zed_camera = None
custom_data_callback = None  # Will hold parsed data for ZED push

# Xsens parsing callback (inspired by xdamtwreceive.py from the repo)
def on_mti7_data_available(device, packet):
    """Callback to parse XDA packet and prepare data for ZED."""
    global custom_data_callback
    if not external_data_recording:
        return

    timestamp = packet.timeStamp * 1000  # Convert to ns (assuming us base; adjust if needed)
    
    # Parse quaternion (w, x, y, z -> x,y,z,w for standard)
    quat = [packet.orientationQuaternion[1], packet.orientationQuaternion[2], 
            packet.orientationQuaternion[3], packet.orientationQuaternion[0]]  # x,y,z,w
    
    # Parse acceleration (x, y, z in m/s²)
    acc = [packet.linearAcceleration[0], packet.linearAcceleration[1], packet.linearAcceleration[2]]
    
    # Parse GPS (Latitude, Longitude, Altitude; defaults if not enabled)
    gps = [getattr(packet, 'positionLLA', [0,0,0])[0],  # Lat
           getattr(packet, 'positionLLA', [0,0,0])[1],  # Lon
           getattr(packet, 'positionLLA', [0,0,0])[2]]  # Alt (m)
    
    # Pack as 9 floats and store for main thread push
    custom_data_callback = (struct.pack('9f', *quat + acc + gps), timestamp)

def init_xsens_mti7(device_id=None):
    """Initialize Xsens MTi-7 using XDA (adapted from repo's device discovery)."""
    try:
        # Add module path if needed (Linux example from repo)
        # module_path = "/home/<yourusername>/.local/lib/python3.8/site-packages/"
        # sys.path.insert(0, module_path)
        
        # Create XDA instance
        xda_instance = xda.XsDeviceApi()
        
        # Discover devices (USB for MTi-7)
        detector_config = xda.XsDetectorConfig()
        detector_config.m_channels = xda.XDC_All  # All channels (USB, Awinda, etc.)
        detected_devices = xda_instance.getDetectedDevices(detector_config)
        
        if not detected_devices:
            raise Exception("No Xsens devices found.")
        
        # Open first device (MTi-7)
        device = detected_devices[0]
        device.open()
        
        # Configure outputs (enable Quaternion, Accel, Position LLA if GPS)
        device.addDataCallback(on_mti7_data_available)
        device.setOutputConfiguration(xda.XO_Quaternion | xda.XO_LinAcc | xda.XO_PositionLLA)
        
        # Start recording/streaming
        device.startRecording()  # Or device.gotoConfig() then device.gotoMeasurement()
        
        print("Xsens MTi-7 initialized via XDA.")
        return device, xda_instance
        
    except Exception as e:
        print(f"Xsens XDA init failed: {e}. Falling back to basic serial.")
        return None, None

def mti7_polling_thread(args):
    """Thread to poll MTi-7 via XDA and push to ZED SVO2."""
    global external_data_recording, zed_camera, custom_data_callback
    custom_data_callback = None
    
    # Try XDA first
    mti_device, xda_inst = init_xsens_mti7()
    use_xda = mti_device is not None
    
    if not use_xda:
        # Fallback to basic serial (as in previous version)
        try:
            ser = serial.Serial(args.external_imu, baudrate=115200, timeout=1)
            print(f"Fallback: Connected to MTi-7 serial on {args.external_imu}")
        except Exception as e:
            print(f"Serial fallback failed: {e}")
            return
        ser = None  # Placeholder for fallback

    sample_count = 0
    while external_data_recording:
        try:
            if use_xda:
                # XDA callback handles parsing; push if data available
                if custom_data_callback:
                    data, ts = custom_data_callback
                    zed_camera.record_custom_data(data, ts)
                    custom_data_callback = None
                    sample_count += 1
                    if sample_count % 100 == 0:
                        print(f"Recorded {sample_count} XDA samples.")
            else:
                # Fallback serial read (simplified CSV-like; adapt as needed)
                line = ser.readline().decode('utf-8').strip()
                if line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        quat = [float(x) for x in parts[0].split(':')[1].split()][:4]
                        acc = [float(x) for x in parts[1].split(':')[1].split()][:3]
                        gps = [float(x) for x in parts[2].split(':')[1].split()][:3]
                        data = struct.pack('9f', *quat + acc + gps)
                        ts = int(time.time() * 1e9)
                        zed_camera.record_custom_data(data, ts)
                        sample_count += 1
                        if sample_count % 100 == 0:
                            print(f"Recorded {sample_count} serial samples.")
            
            time.sleep(0.01)  # ~100 Hz; sync to MTi-7 rate
        except Exception as e:
            print(f"MTi-7 polling error: {e}")
    
    if use_xda:
        mti_device.stopRecording()
        mti_device.close()
        xda_inst.destruct()
    else:
        if ser:
            ser.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Record SVO2 from ZED X with Xsens MTi-7 (XDA parsing).')
    parser.add_argument('--resolution', type=str, default='HD1080', choices=['HD1080', 'HD2K', '2K'],
                        help='Camera resolution (default: HD1080)')
    parser.add_argument('--compression', type=str, default='H265', choices=['H264', 'H265'],
                        help='Compression mode (default: H265)')
    parser.add_argument('--fps', type=int, default=30, choices=[15, 30, 60],
                        help='Camera FPS (default: 30)')
    parser.add_argument('--external-imu', type=str, default=None,
                        help='USB port or ID for MTi-7 (e.g., /dev/ttyUSB0 for fallback; XDA auto-detects).')
    parser.add_argument('--output', type=str, default='zedx_svo2_with_mti7.svo',
                        help='Output SVO2 filename (default: zedx_svo2_with_mti7.svo)')
    parser.add_argument('--duration', type=int, default=60,
                        help='Auto-stop after N seconds (default: 60; 0 for manual)')
    return parser.parse_args()

def main():
    global external_data_recording, zed_camera
    args = parse_arguments()

    # ZED setup (unchanged)
    res_map = {'HD1080': sl.RESOLUTION.HD1080, 'HD2K': sl.RESOLUTION.HD2K, '2K': sl.RESOLUTION.HD2K}
    comp_map = {'H264': sl.COMPRESSION_MODE.H264, 'H265': sl.COMPRESSION_MODE.H265}
    init_params = sl.InitParameters()
    init_params.camera_resolution = res_map[args.resolution]
    init_params.camera_fps = args.fps
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.coordinate_units = sl.UNIT.METER
    init_params.sdk_verbose = True

    zed_camera = sl.Camera()
    status = zed_camera.open(init_params)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open ZED X: {status}")
        sys.exit(1)

    tracking_params = sl.PositionalTrackingParameters()
    tracking_params.enable_imu_fusion = True
    zed_camera.enable_positional_tracking(tracking_params)

    recording_param = sl.RecordingParameters()
    recording_param.video_filename = args.output
    recording_param.compression_mode = comp_map[args.compression]
    recording_param.save_video = True

    status = zed_camera.enable_recording(recording_param)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to start SVO2 recording: {status}")
        zed_camera.close()
        sys.exit(1)

    print(f"SVO2 recording started: {args.output} (Res: {args.resolution}, FPS: {args.fps}, Comp: {args.compression})")
    if args.external_imu:
        print(f"Initializing MTi-7 (XDA preferred)...")
    print("Controls: SPACE to pause/resume, ESC to stop. Auto-stop in {}s.".format(args.duration))

    # Start MTi-7 thread
    external_data_recording = True
    if args.external_imu:
        mti_thread = threading.Thread(target=mti7_polling_thread, args=(args,))
        mti_thread.daemon = True
        mti_thread.start()

    # ZED recording loop (unchanged)
    start_time = time.time()
    key = ''
    paused = False
    while key != 27:
        if args.duration > 0 and (time.time() - start_time) > args.duration:
            print("Auto-stop reached.")
            break

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            paused = not paused
            if paused:
                zed_camera.disable_recording()
                print("Paused.")
            else:
                zed_camera.enable_recording(recording_param)
                print("Resumed.")

        if not paused and zed_camera.grab() == sl.ERROR_CODE.SUCCESS:
            pose = sl.Pose()
            zed_camera.get_position(pose, sl.REFERENCE_FRAME.WORLD)
            print(f"ZED Pose: {pose.get_translation().get()}")

    # Cleanup
    external_data_recording = False
    zed_camera.disable_recording()
    zed_camera.disable_positional_tracking()
    zed_camera.close()
    cv2.destroyAllWindows()
    print("SVO2 recording finished.")

if __name__ == "__main__":
    main()