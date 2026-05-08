from nuscenes.nuscenes import NuScenes
from ultralytics import YOLO
import cv2
import numpy as np
import os
import time
import csv
from numba import cuda
import math

# 1. SETUP & INITIALIZATION

DATAROOT = "C:\\Users\\banuk\\Downloads\\v1.0-mini"
FRAMES_PER_TEST = 50  # 50 frames for GPU, then 50 frames for CPU
CSV_FILENAME = "cpu_vs_gpu_benchmark.csv"

print("Loading nuScenes database...")
nusc = NuScenes(version='v1.0-mini', dataroot=DATAROOT, verbose=False)

print("Loading YOLOv8 AI Brain...")
model = YOLO("yolov8n.pt") 

# --- CUDA Kernel ---
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

# 2. BENCHMARK LOGGING SETUP

with open(CSV_FILENAME, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Hardware_Target", "Frame_Number", "Transfer_In_ms", "Blur_Execution_ms", "Transfer_Out_ms", "YOLO_Inference_ms", "Total_Frame_Time_ms"])

    my_scene = nusc.scene[0]

    # PHASE 1: GPU BENCHMARK

    print(f"\n--- Starting GPU Benchmark ({FRAMES_PER_TEST} frames) ---")
    current_sample = nusc.get('sample', my_scene['first_sample_token'])

    for frame_count in range(FRAMES_PER_TEST):
        if current_sample['next'] == '': break

        sensor_data = nusc.get('sample_data', current_sample['data']['CAM_FRONT'])
        frame = cv2.imread(os.path.join(DATAROOT, sensor_data['filename']))
        height, width, channels = frame.shape

        threads_per_block = (16, 16)
        blocks_per_grid_x = math.ceil(width / threads_per_block[0])
        blocks_per_grid_y = math.ceil(height / threads_per_block[1])
        blocks_per_grid = (blocks_per_grid_x, blocks_per_grid_y)

        t_total_start = time.perf_counter()

        # GPU Transfer IN
        t0 = time.perf_counter()
        d_frame_in = cuda.to_device(frame)
        d_frame_out = cuda.device_array((height, width, channels), dtype=np.uint8)
        t_transfer_in = (time.perf_counter() - t0) * 1000

        # GPU Execution
        t1 = time.perf_counter()
        for _ in range(3):
            cuda_gaussian_blur[blocks_per_grid, threads_per_block](d_frame_in, d_frame_out, width, height)
            d_frame_in = d_frame_out 
        cuda.synchronize()
        t_execution = (time.perf_counter() - t1) * 1000

        # GPU Transfer OUT
        t2 = time.perf_counter()
        processed_frame = d_frame_out.copy_to_host()
        t_transfer_out = (time.perf_counter() - t2) * 1000

        # YOLO Inference (Default is GPU since PyTorch automatically uses CUDA if available)
        t3 = time.perf_counter()
        results = model(processed_frame, verbose=False)
        t_yolo = (time.perf_counter() - t3) * 1000

        t_total_time = (time.perf_counter() - t_total_start) * 1000

        writer.writerow(["GPU", frame_count + 1, round(t_transfer_in, 2), round(t_execution, 2), round(t_transfer_out, 2), round(t_yolo, 2), round(t_total_time, 2)])
        current_sample = nusc.get('sample', current_sample['next'])

    # PHASE 2: CPU BENCHMARK

    print(f"\n--- Starting CPU Benchmark ({FRAMES_PER_TEST} frames) ---")
    # Reset back to the first frame of the scene so the exact same images are tested
    current_sample = nusc.get('sample', my_scene['first_sample_token'])

    for frame_count in range(FRAMES_PER_TEST):
        if current_sample['next'] == '': break

        sensor_data = nusc.get('sample_data', current_sample['data']['CAM_FRONT'])
        frame = cv2.imread(os.path.join(DATAROOT, sensor_data['filename']))

        t_total_start = time.perf_counter()

        # No Transfer IN/OUT required for CPU (Data is already in system RAM)
        t_transfer_in = 0.0
        t_transfer_out = 0.0

        # CPU Execution (Using OpenCV's highly optimized C++ backend)
        t1 = time.perf_counter()
        processed_frame = frame
        for _ in range(3):
            # A 3x3 Gaussian Blur to mimic the CUDA kernel
            processed_frame = cv2.GaussianBlur(processed_frame, (3, 3), 0)
        t_execution = (time.perf_counter() - t1) * 1000

        # YOLO Inference (Force device='cpu' to prevent it using the GPU)
        t3 = time.perf_counter()
        results = model(processed_frame, device='cpu', verbose=False)
        t_yolo = (time.perf_counter() - t3) * 1000

        t_total_time = (time.perf_counter() - t_total_start) * 1000

        writer.writerow(["CPU", frame_count + 1, t_transfer_in, round(t_execution, 2), t_transfer_out, round(t_yolo, 2), round(t_total_time, 2)])
        current_sample = nusc.get('sample', current_sample['next'])

print(f"\nBenchmark Complete! Data saved to {CSV_FILENAME}")
