# Heterogeneous Compute Architectures for Autonomous Emergency Braking 🚗⚡

**University Final Year Engineering Project (Module: XE636)**

This repository contains the empirical data logs and visual simulation results for a custom Hardware-in-the-Loop (HIL) architecture. The project contrasts the non-deterministic latency of a CPU/GPU perception pipeline against the deterministic, zero-jitter actuation of a Verilog Finite State Machine on an Artix-7 FPGA. Furthermore the project deploys an Autonomous Braking System using the GPU and FPGA in a hybrid configuration.

---
### Code
The Python scripts and Verilog Code for the project
* [HIL Simulation Script](hil_simulation_v2.py)
* [CPU vs GPU Benchmark Script](benchmark_cpu_vs_gpu.py)
---
### 🎥 Visual System Demonstrations
*Watch the closed-loop system dynamically calculate Danger, Steering, Throttle, and Brake across the nuScenes dataset.*

* [🎬 HIL Simulation Run 01](./nuScenes_AEB_CUDA_demo_0.mp4)
* [🎬 HIL Simulation Run 02](./nuScenes_AEB_CUDA_demo_1.mp4)
* [🎬 HIL Simulation Run 03](./nuScenes_AEB_CUDA_demo_2.mp4)
* [🎬 HIL Simulation Run 04](./nuScenes_AEB_CUDA_demo_3.mp4)
* [🎬 HIL Simulation Run 05](./nuScenes_AEB_CUDA_demo_4.mp4)
* [🎬 HIL Simulation Run 06](./nuScenes_AEB_CUDA_demo_5.mp4)
* [🎬 HIL Simulation Run 07](./nuScenes_AEB_CUDA_demo_6.mp4)
* [🎬 HIL Simulation Run 08](./nuScenes_AEB_CUDA_demo_7.mp4)
* [🎬 HIL Simulation Run 09](./nuScenes_AEB_CUDA_demo_8.mp4)
* [🎬 HIL Simulation Run 10](./nuScenes_AEB_CUDA_demo_9.mp4)

---

### 📊 Data Logs
*The raw CSV telemetry captured during the simulations.*

**CPU vs. GPU Benchmarks (Execution Latency & PCIe Bottlenecks)**
* [📈 Benchmark Data 0](./cpu_vs_gpu_benchmark_0.csv)
* [📈 Benchmark Data 1](./cpu_vs_gpu_benchmark_1.csv)
* [📈 Benchmark Data 2](./cpu_vs_gpu_benchmark_2.csv)
* [📈 Benchmark Data 3](./cpu_vs_gpu_benchmark_3.csv)
* [📈 Benchmark Data 4](./cpu_vs_gpu_benchmark_4.csv)
* [📈 Benchmark Data 5](./cpu_vs_gpu_benchmark_5.csv)
* [📈 Benchmark Data 6](./cpu_vs_gpu_benchmark_6.csv)
* [📈 Benchmark Data 7](./cpu_vs_gpu_benchmark_7.csv)
* [📈 Benchmark Data 8](./cpu_vs_gpu_benchmark_8.csv)
* [📈 Benchmark Data 9](./cpu_vs_gpu_benchmark_9.csv)

**FPGA Closed-Loop Telemetry (9600-baud UART)**
* [📉 FPGA Log 0](./fpga_closed_loop_log_0.csv)
* [📉 FPGA Log 1](./fpga_closed_loop_log_1.csv)
* [📉 FPGA Log 2](./fpga_closed_loop_log_2.csv)
* [📉 FPGA Log 3](./fpga_closed_loop_log_3.csv)
* [📉 FPGA Log 4](./fpga_closed_loop_log_4.csv)
* [📉 FPGA Log 5](./fpga_closed_loop_log_5.csv)
* [📉 FPGA Log 6](./fpga_closed_loop_log_6.csv)
* [📉 FPGA Log 7](./fpga_closed_loop_log_7.csv)
* [📉 FPGA Log 8](./fpga_closed_loop_log_8.csv)
* [📉 FPGA Log 9](./fpga_closed_loop_log_9.csv)
