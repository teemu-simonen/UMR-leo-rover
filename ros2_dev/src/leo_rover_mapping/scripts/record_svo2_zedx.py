import pyzed.sl as sl
import cv2
import argparse
import time

def main():
    parser = argparse.ArgumentParser(description="Clean SVO2 recorder for ZED X")
    parser.add_argument("--resolution", type=str, default="HD1080",
                        choices=["HD1080", "HD2K", "2K"],
                        help="Resolution: HD1080 (1920x1080), HD2K (2208x1242), 2K (4416x1242)")
    parser.add_argument("--fps", type=int, default=30,
                        choices=[15, 30, 60], help="FPS (respect camera limits)")
    parser.add_argument("--compression", type=str, default="H265",
                        choices=["H264", "H265"], help="H264 or H265 (H265 = smaller files)")
    parser.add_argument("--output", type=str, default="zedx_capture.svo",
                        help="Output filename (will be SVO2)")
    parser.add_argument("--duration", type=int, default=0,
                        help="Auto-stop after N seconds (0 = manual stop)")
    parser.add_argument("--no-preview", action="store_true",  
                        help="Disable live OpenCV preview (headless mode)")

    args = parser.parse_args()

    # Map arguments to ZED enums
    res_map = {
        "HD1080": sl.RESOLUTION.HD1080,
        "HD2K":   sl.RESOLUTION.HD2K,
        "2K":     sl.RESOLUTION.HD2K   # 2K uses the same enum as HD2K
    }
    comp_map = {
        "H264": sl.COMPRESSION_MODE.H264,
        "H265": sl.COMPRESSION_MODE.H265
    }

    # Initialize ZED
    init = sl.InitParameters()
    init.camera_resolution = res_map[args.resolution]
    init.camera_fps = args.fps
    init.depth_mode = sl.DEPTH_MODE.PERFORMANCE      # or ULTRA for max accuracy
    init.coordinate_units = sl.UNIT.METER
    init.sdk_verbose = True

    zed = sl.Camera()
    status = zed.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"[ERROR] Cannot open ZED X: {status}")
        exit(1)

    # Enable positional tracking → IMU + VIO poses stored in SVO2
    tracking_params = sl.PositionalTrackingParameters()
    tracking_params.enable_imu_fusion = True
    zed.enable_positional_tracking(tracking_params)

    # Recording parameters (SVO2 is automatic)
    rec_params = sl.RecordingParameters()
    rec_params.video_filename = args.output
    rec_params.compression_mode = comp_map[args.compression]

    status = zed.enable_recording(rec_params)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"[ERROR] Cannot start recording: {status}")
        zed.close()
        exit(1)

    print(f"\nRecording started!")
    print(f"   Resolution : {args.resolution} @ {args.fps} FPS")
    print(f"   Compression: {args.compression}")
    print(f"   Output     : {args.output} (SVO2 format)")
    print(f"   Duration   : {'manual' if args.duration==0 else f'{args.duration}s'}")
    print("\nControls: SPACE = pause/resume, ESC = stop\n")

    runtime = sl.RuntimeParameters()
    left_image = sl.Mat()

    start_time = time.time()
    paused = False

    try:
        while True:
            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                print("Auto-stop timer reached.")
                break

            if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:
                # Live preview (optional)
                if not args.no_preview:
                    zed.retrieve_image(left_image, sl.VIEW.LEFT)
                    cv2.imshow("ZED X Live", left_image.get_data())
                
                # Keyboard control
                key = cv2.waitKey(1) & 0xFF
                if key == 27:        # ESC
                    break
                elif key == 32:      # Space
                    paused = not paused
                    if paused:
                        zed.disable_recording()
                        print("Paused (press Space to resume)")
                    else:
                        zed.enable_recording(rec_params)
                        print("Resumed")

            if paused:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    finally:
        zed.disable_recording()
        zed.disable_positional_tracking()
        zed.close()
        cv2.destroyAllWindows()
        print(f"Recording saved → {args.output}")

if __name__ == "__main__":
    main()