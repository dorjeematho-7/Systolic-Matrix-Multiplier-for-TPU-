# Systolic-Matrix-Multiplier-for-TPU-  

# Background
The primary motivation for developing this architecture is to address the immense processing demands of modern data-intensive workloads. Because matrix multiplication is the foundational operation for AI Compute, general purpose processors are too slow and use too much power for these specific tasks. Implementing this system provides a high-performance, low-latency hardware solution optimized for spatial data flow. I also want to build a TPU so this is my first step.  

Typical matrix multiplation follows this sequence  
  
<img width="1605" height="742" alt="image" src="https://github.com/user-attachments/assets/bc0608f7-c1a1-4d2d-9f8a-9ae55462d5c3" />

Systolic Matrix Mutlipliers utilize the concept of data recycling and data movement between processing units to improve compute speed and power. The following youtube video demonstrates the movement of data in a Systollic matrix Multiplier https://www.youtube.com/watch?v=cmy7LBaWuZ8 (This video helped me alot at the beginning)

# Data Movement Video Demonstration

https://github.com/user-attachments/assets/1e3b6a05-9f5c-4da1-99bc-5040cb8c225f


# Introduction

This project will be the construction of a systolic Matrix Multiplier, which I will be using to build a TPU later on in the semester (Most likely during winter break).  

To start off, lets investigate the Architecture that I have constructed after doing some research

<img width="742" height="691" alt="image" src="https://github.com/user-attachments/assets/df2a879a-2b75-4795-a9e6-0eeedb091bec" />  

                                                            FIGURE 1

  
  
Shoutout to  DR. SHIRSHENDU ROY for providing academic information on Systolic arrays as it helped me defined my architecture.


  ## Parameters
- `N` = 3
- `DATA_W` = 8
- `ACC_W` = 32
- `K_MAX` = 16

## Inputs
- `clk`
- `rst_n`
- `s0`
- `s1`
- `k`
- `in_valid`
- `acc_clr`
- `a_we`, `a_wbank`, `a_wtile`, `a_wk`, `a_wdata`
- `b_we`, `b_wbank`, `b_wtile`, `b_wk`, `b_wdata`

## Outputs
- `c`

# Verification



# Physical Design

