from nuscenes.nuscenes import NuScenes
from ultralytics import YOLO
import cv2
import numpy as np
import os
import serial
import time
import csv
from numba import cuda
import math

# 1. CONFIGURATION & SETUP

DATAROOT = "C:\\Users\\banuk\\Downloads\\v1.0-mini"
COM_PORT = 'COM6'
BAUD_RATE = 9600
OUTPUT_VIDEO = "nuScenes_AEB_CUDA_demo.mp4"
LOG_FILENAME = "fpga_closed_loop_log.csv"

print("Loading nuScenes database...")
nusc = NuScenes(version='v1.0-mini', dataroot=DATAROOT, verbose=False)

print("Loading YOLOv8 AI Brain...")
model = YOLO("yolov8n.pt") 

# --- UART Setup ---
try:
    # A 0.05s timeout ensures that the video doesn't freeze if the FPGA unplugs, 
    # but gives plenty of time (50ms) to receive 4 bytes at 9600 baud (~4ms)
    fpga_port = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.05)
    print(f"Successfully connected to FPGA on {COM_PORT}")
except serial.SerialException:
    print(f"Warning: Could not connect to FPGA on {COM_PORT}. Running in software-only mode.")
    fpga_port = None

# 2. CUSTOM CUDA KERNELS

@cuda.jit
def cuda_gaussian_blur(img_in, img_out, w, h):
    x, y = cuda.grid(2)
    if 0 < x < w - 1 and 0 < y < h - 1:
        for c in range(3): 
            val = (
                img_in[y-1, x-1, c] * 1 + img_in[y-1, x, c] * 2 + img_in[y-1, x+1, c] * 1 +
                img_in[y, x-1, c] * 2   + img_in[y, x, c] * 4   + img_in[y, x+1, c] * 2 +
                img_in[y+1, x-1, c] * 1 + img_in[y+1, x, c] * 2 + img_in[y+1, x+1, c] * 1
            ) / 16.0 
            img_out[y, x, c] = val

# 3. INITIALIZE SCENE & VIDEO WRITER

my_scene = nusc.scene[0]
current_sample = nusc.get('sample', my_scene['first_sample_token'])

first_frame_data = nusc.get('sample_data', current_sample['data']['CAM_FRONT'])
first_frame_path = os.path.join(DATAROOT, first_frame_data['filename'])
first_frame = cv2.imread(first_frame_path)
height, width, channels = first_frame.shape

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, 10.0, (width, height)) 

# 4. MAIN HIL SIMULATION LOOP (WITH LOGGING)

print(f"Starting Simulation... Logging data to {LOG_FILENAME}. Press 'q' to quit.")

# Open the CSV file and keep it open while the simulation runs
with open(LOG_FILENAME, mode='w', newline='') as log_file:
    csv_writer = csv.writer(log_file)
    # Write the column headers
    csv_writer.writerow(["Frame", "Danger_Sent", "Steering_Sent", "FPGA_Brake_Recv", "FPGA_Throttle_Recv", "FPGA_Steer_Recv"])
    
    frame_count = 0

    while True:
        frame_count += 1
        sensor_data = nusc.get('sample_data', current_sample['data']['CAM_FRONT'])
        img_filename = os.path.join(DATAROOT, sensor_data['filename'])
        frame = cv2.imread(img_filename)
        if frame is None: break

        # --- A. CUDA Environment Simulation ---
        d_frame_A = cuda.to_device(frame)
        d_frame_B = cuda.device_array((height, width, channels), dtype=np.uint8)
        
        threads_per_block = (16, 16)
        blocks_per_grid_x = math.ceil(width / threads_per_block[0])
        blocks_per_grid_y = math.ceil(height / threads_per_block[1])
        blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y)

        # 3 Passes of Ping-Pong Buffering to prevent race conditions
        cuda_gaussian_blur[blocks_per_grid, threads_per_block](d_frame_A, d_frame_B, width, height)
        cuda_gaussian_blur[blocks_per_grid, threads_per_block](d_frame_B, d_frame_A, width, height)
        cuda_gaussian_blur[blocks_per_grid, threads_per_block](d_frame_A, d_frame_B, width, height)
        
        processed_frame = d_frame_B.copy_to_host()

        # --- B. AI Inference (YOLOv8) ---
        results = model(processed_frame, verbose=False)
        annotated_frame = results[0].plot()

        # --- C. Control Logic ---
        max_height = 0
        target_center_x = width // 2 

        for box in results[0].boxes:
            if int(box.cls) == 2: 
                x_center, y_center, w, h = box.xywh[0]
                if h > max_height:
                    max_height = h.item()
                    target_center_x = x_center.item()

        danger_level = min(255, int((max_height / 900) * 255))
        steering_val = int((target_center_x / width) * 255)

        # --- D. BI-DIRECTIONAL UART & LOGGING ---
        fpga_brake = 0
        fpga_throttle = 0
        fpga_steer_echo = 0

        if fpga_port is not None:
            # 1. Send 3 bytes to FPGA
            fpga_port.write(bytes([0xFF, danger_level, steering_val]))
            
            # 2. Wait and read 4 bytes back from FPGA
            response = fpga_port.read(4)
            
            # 3. Parse the data if it's a valid packet
            if len(response) == 4 and response[0] == 0xFF:
                fpga_brake = response[1]
                fpga_throttle = response[2]
                fpga_steer_echo = response[3]
                
                print(f"Frame {frame_count:3} | Danger: {danger_level:3} -> FPGA Brake: {fpga_brake:3} | Throttle: {fpga_throttle:3}")
            else:
                fpga_port.reset_input_buffer() # Clear corrupted data

        # Log the exact exchange to the CSV
        csv_writer.writerow([frame_count, danger_level, steering_val, fpga_brake, fpga_throttle, fpga_steer_echo])

        # --- E. Visualization ---
        color = (0, 255, 0)
        if danger_level > 80: color = (0, 255, 255)
        if danger_level > 150: color = (0, 0, 255) 
        
        # Line 1: What the PC AI Sees
        cv2.putText(annotated_frame, f"AI DANGER: {danger_level} | AI STEER: {steering_val}", (30, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
        
        # Line 2: What the FPGA Decides
        cv2.putText(annotated_frame, f"FPGA BRAKE: {fpga_brake} | FPGA THROT: {fpga_throttle}", (30, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 100, 100), 3)

        out.write(annotated_frame) 
        cv2.imshow('nuScenes HIL Simulation - CUDA Blur', annotated_frame)

        if current_sample['next'] == '': break 
        current_sample = nusc.get('sample', current_sample['next'])
        if cv2.waitKey(200) & 0xFF == ord('q'): break

# 5. CLEANUP & SHUTDOWN

out.release() 
cv2.destroyAllWindows()
if fpga_port is not None: fpga_port.close()
print(f"Simulation complete. Full data log saved to {LOG_FILENAME}")