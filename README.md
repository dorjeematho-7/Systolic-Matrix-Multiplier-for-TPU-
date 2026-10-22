# Systolic-Matrix-Multiplier-for-TPU-  

# Background
The primary motivation for developing this architecture is to address the immense processing demands of modern data-intensive workloads. Because matrix multiplication is the foundational operation for AI Compute, general purpose processors are too slow and use too much power for these specific tasks. Implementing this system provides a high-performance, low-latency hardware solution optimized for spatial data flow. I also want to build a TPU so this is my first step.  

Typical matrix multiplation follows this sequence  
  
<img width="1605" height="742" alt="image" src="https://github.com/user-attachments/assets/bc0608f7-c1a1-4d2d-9f8a-9ae55462d5c3" />  
  
                                                            FIGURE 1

Systolic Matrix Mutlipliers utilize the concept of data recycling and data movement between processing units to improve compute speed and power. The following youtube video demonstrates the movement of data in a Systollic matrix Multiplier https://www.youtube.com/watch?v=cmy7LBaWuZ8 (This video helped me alot at the beginning)

# Data Movement Video Demonstration of the implemented system


https://github.com/user-attachments/assets/c0cffba9-0a1e-4498-ab5a-b2f69f707514

  

                                                              FIGURE 2


# Introduction
This project is a N×N systolic array matrix multiplier (but for the examples i show a 3x3) written in SystemVerilog. A systolic array is a grid of identical processing elements (PEs) that pass data to their neighbours every clock cycle. Each value is read from memory once and reused as it moves through the array, which is why this structure is used in AI accelerators such as Google’s TPU.

The design is output-stationary: rows of A flow left to right, columns of B flow top to bottom, and each PE multiplies the values passing through it and keeps a running sum of one output element. Delay registers on the inputs stagger the data so matching values meet in the right PE on the right cycle. Two select signals (S0 and S1) switch between tiles of A and B, so the 3×3 array computes a 6×6 result one 3×3 block at a time.

Inputs are signed 8-bit integers (INT8) and results are accumulated in 32 bits. 
  
To start off, lets investigate the Architecture that I have constructed after doing some research

# Datapath Architecture


<img width="2000" height="1900" alt="image" src="https://github.com/user-attachments/assets/4f92a00e-bbd3-4b14-80d7-4666c31656fb" />





                                                            FIGURE 3
  

      
Big shoutout to  **DR. SHIRSHENDU ROY** for providing academic information on Systolic arrays as it helped me defined my architecture.



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



# Physical Design




# Results
<img width="590" height="361" alt="image" src="https://github.com/user-attachments/assets/67a9edb8-f499-470c-9a72-695d904ca361" />

