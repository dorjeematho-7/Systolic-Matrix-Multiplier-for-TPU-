# Systolic-Matrix-Multiplier-for-TPU-  

# Background
The primary motivation for developing this architecture is to address the immense processing demands of modern data-intensive workloads. Because matrix multiplication is the foundational operation for AI Compute, general purpose processors are too slow and use too much power for these specific tasks. Implementing this system provides a high-performance, low-latency hardware solution optimized for spatial data flow. I also want to build a TPU so this is my first step.  

Typical matrix multiplation follows this sequence  
  
<img width="1605" height="742" alt="image" src="https://github.com/user-attachments/assets/bc0608f7-c1a1-4d2d-9f8a-9ae55462d5c3" />  
  
                                                            FIGURE 1

Systolic Matrix Mutlipliers utilize the concept of data recycling and data movement between processing units to improve compute speed and power. The following youtube video demonstrates the movement of data in a Systollic matrix Multiplier https://www.youtube.com/watch?v=cmy7LBaWuZ8 (This video helped me alot at the beginning)

# Data Movement Video Demonstration of the implemented system





https://github.com/user-attachments/assets/9696aa53-d634-4b2d-9adc-84d57e8905b6




                                                              FIGURE 2


# Introduction
This project is a N×N systolic array matrix multiplier written in SystemVerilog. A systolic array is a grid of identical processing elements (PEs) that pass data to their neighbours every clock cycle. Each value is read from memory once and reused as it moves through the array, which is why this structure is used in AI accelerators such as Google’s TPU.

The design is output-stationary: rows of A flow left to right, columns of B flow top to bottom, and each PE multiplies the values passing through it and keeps a running sum of one output element. Delay registers on the inputs stagger the data so matching values meet in the right PE on the right cycle. Two select signals (S0 and S1) switch between tiles of A and B, so the 3×3 array computes a 6×6 result one 3×3 block at a time.

Inputs are signed 8-bit integers (INT8) and results are accumulated in 32 bits. 
  
To start off, lets investigate the Architecture that I have constructed after doing some research

# Datapath Architecture


<img width="2000" height="1900" alt="image" src="https://github.com/user-attachments/assets/4f92a00e-bbd3-4b14-80d7-4666c31656fb" />





                                                            FIGURE 3
  

      
Big shoutout to  **DR. SHIRSHENDU ROY** for providing academic information on Systolic arrays as it helped me defined my architecture.

Link to his article:  
https://digitalsystemdesign.in/systolic-matrix-multiplier/?srsltid=AYCX9vLirNlyNZZZifU2sXZRRwUCW0qnUKk8uGzstvZG2AaEvf6vDVec



  ### Parameters
- `N` = 3
- `DATA_W` = 8
- `ACC_W` = 32
- `K_MAX` = 16

### Inputs
- `clk`
- `rst_n`
- `s0`
- `s1`
- `k`
- `in_valid`
- `acc_clr`
- `a_we`, `a_wbank`, `a_wtile`, `a_wk`, `a_wdata`
- `b_we`, `b_wbank`, `b_wtile`, `b_wk`, `b_wdata`

### Outputs
- `c`

# Control Logic
- The state diagram here is pretty simple, we need three states, LOAD, COMPUTE, and OUTPUT. The busy signal is high during compute and output, and so its important to mention now that if data A and B arrive while busy is high, write enable is gated with the state == LOAD, and so the data A and B are essentially dropped. In Compute the Counter runs. While count < K, feed column k = count from the buffers into the skew logic. After that, feed zeros while the wavefront drains. For the OUTPUT state, Accumulators hold their values. I then shall make a testbench to read C values
- <img width="1722" height="553" alt="image" src="https://github.com/user-attachments/assets/fd34972a-c1d2-4dfa-834e-84fcafe0c81c" />

# Verification
- Up until now I've been using SystemVerilog to write testbenches and using ModelSim to evaluate them, well now its time I learn a new skill and write testbenches with cocotb, so this project provides motivation for new verification methods!

# Results 

## 3x3 Case

<img width="800" height="340" alt="timesteps_3x3" src="https://github.com/user-attachments/assets/297204c8-b91b-4cde-af3c-f1cfd1c9ba86" />  

## 6x6 Case
<img width="800" height="340" alt="timesteps_6x6" src="https://github.com/user-attachments/assets/e90a2456-ed33-48e7-b906-2187c7000f65" />

## 12x12 Case
<img width="800" height="340" alt="timesteps_12x12" src="https://github.com/user-attachments/assets/c3a2259e-9413-4f75-8337-65acb07939a6" />

## Case Comparison
<img width="1000" height="540" alt="timesteps_scaling" src="https://github.com/user-attachments/assets/67b24d74-cb42-4e6e-97db-af33e102fa8c" />

## Summary of the Results  

Essentially, the charts compare how many time steps an N×N matrix multiplication takes when operations are done one at a time in standard matrix mult vs on an N×N systolic array which I have implemented here. Done one at a time, the multiply needs 2N³ − N² steps: 45 for a 3×3, 396 for a 6×6 and 3,312 for a 12×12. The systolic array finishes in 3N − 2 clock cycles (in our case 3N- 3 in the video cuz we started at zero, but OVERALL 3N-2), each counted as a multiply step and an add step, which gives 2(3N − 2) steps: 14, 32 and 68 for the same sizes. That's a speedup of 3.2×, 12.4× and 48.7×. The array doesn't do any less arithmetic. It spreads the same work across N² processing elements running in parallel, and keeps them fed by passing each input from neighbour to neighbour so it's reused N times instead of being fetched again. Because the one-at-a-time cost grows as N³ while the systolic time grows only as N, the advantage widens rapidly with matrix size. These are ideal figures: they leave out the time to load the matrices into the array and read the results back out, and the cycles when the grid is only partly busy as data flows in and out, both of which matter most for small matrices.





