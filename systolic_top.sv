// top level of the system. just wiring and system logic 
module systolic_top #(
    parameter int N = 3,
    parameter int K = 2,
    parameter int DW = 8,
    parameter int AW = 2 * DW + $clog2(K),
    parameter int KW = (K > 1) ? $clog2(K) : 1,
    parameter int NW = (N > 1) ? $clog2(N) : 1
) (
    input logic clk,
    input logic rst_n,

    input logic a_we,
    input logic [NW-1:0] a_bank,
    input logic [KW-1:0] a_addr,
    input logic [DW-1:0] a_wdata,

    input logic b_we,
    input logic [NW-1:0] b_bank,
    input logic [KW-1:0] b_addr,
    input logic [DW-1:0] b_wdata,

    input logic start,
    output logic busy,
    output logic done,
    output logic [N*N*AW-1:0] c_flat
);

    logic clear;
    logic feed_v;
    logic [KW-1:0] s0, s1;

    controller #(.N(N), .K(K)) u_ctrl (
        .clk   (clk),
        .rst_n (rst_n),
        .start (start),
        .clear (clear),
        .s0    (s0),
        .s1    (s1),
        .feed_v(feed_v),
        .busy  (busy),
        .done  (done)
    );

    logic [DW-1:0] a_rd [N];
    logic [DW-1:0] b_rd [N];
    logic [DW-1:0] a_mux [N];
    logic [DW-1:0] b_mux [N];
    logic signed [DW-1:0] a_west [N];
    logic a_west_v [N];
    logic signed [DW-1:0] b_north [N];
    logic b_north_v [N];
    logic signed [AW-1:0] acc [N][N];

    for (genvar i = 0; i < N; i++) begin : g_lane
        operand_mem #(.DW(DW), .K(K)) u_amem (
            .clk  (clk),
            .we   (a_we && !busy && a_bank == NW'(i)),
            .waddr(a_addr),
            .wdata(a_wdata),
            .sel  (s0),
            .rdata(a_rd[i])
        );

        operand_mem #(.DW(DW), .K(K)) u_bmem (
            .clk  (clk),
            .we   (b_we && !busy && b_bank == NW'(i)),
            .waddr(b_addr),
            .wdata(b_wdata),
            .sel  (s1),
            .rdata(b_rd[i])
        );

        // Feed zeros whenever the controller is not streaming operands.
        assign a_mux[i] = feed_v ? a_rd[i] : '0;
        assign b_mux[i] = feed_v ? b_rd[i] : '0;

        // Lane i is delayed by i cycles: 0, 1 and 2 D boxes in the drawing.
        skew_reg #(.DW(DW), .DEPTH(i)) u_askew (
            .clk  (clk),
            .rst_n(rst_n),
            .d_in (a_mux[i]),
            .v_in (feed_v),
            .d_out(a_west[i]),
            .v_out(a_west_v[i])
        );

        skew_reg #(.DW(DW), .DEPTH(i)) u_bskew (
            .clk  (clk),
            .rst_n(rst_n),
            .d_in (b_mux[i]),
            .v_in (feed_v),
            .d_out(b_north[i]),
            .v_out(b_north_v[i])
        );
    end

    systolic_array #(.N(N), .DW(DW), .AW(AW)) u_array (
        .clk      (clk),
        .rst_n    (rst_n),
        .clear    (clear),
        .a_west   (a_west),
        .a_west_v (a_west_v),
        .b_north  (b_north),
        .b_north_v(b_north_v),
        .acc      (acc)
    );

    for (genvar i = 0; i < N; i++) begin : g_out_row
        for (genvar j = 0; j < N; j++) begin : g_out_col
            assign c_flat[(i*N+j)*AW +: AW] = acc[i][j];
        end
    end

endmodule
