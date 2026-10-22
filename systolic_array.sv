// N x N grid of PEs. Row i takes its A stream on the west edge and
// column j takes its B stream on the north edge. Both must already be skewed.
module systolic_array #(
    parameter int N = 3,
    parameter int DW = 8,
    parameter int AW = 17
) (
    input logic clk,
    input logic rst_n,
    input logic clear,
    input var logic signed [DW-1:0] a_west [N],
    input var logic a_west_v [N],
    input var logic signed [DW-1:0] b_north [N],
    input var logic b_north_v [N],
    output logic signed [AW-1:0] acc [N][N]
);

    // a_h[i][j] is the A operand entering PE(i,j); column N is the east edge.
    // b_v[i][j] is the B operand entering PE(i,j); row N is the south edge.
    logic signed [DW-1:0] a_h [N][N+1];
    logic a_hv [N][N+1];
    logic signed [DW-1:0] b_v [N+1][N];
    logic b_vv [N+1][N];

    for (genvar i = 0; i < N; i++) begin : g_edge
        assign a_h [i][0] = a_west[i];
        assign a_hv[i][0] = a_west_v[i];
        assign b_v [0][i] = b_north[i];
        assign b_vv[0][i] = b_north_v[i];
    end

    for (genvar i = 0; i < N; i++) begin : g_row
        for (genvar j = 0; j < N; j++) begin : g_col
            pe #(.DW(DW), .AW(AW)) u_pe (
                .clk   (clk),
                .rst_n (rst_n),
                .clear (clear),
                .a_in  (a_h [i][j]),
                .a_vin (a_hv[i][j]),
                .b_in  (b_v [i][j]),
                .b_vin (b_vv[i][j]),
                .a_out (a_h [i][j+1]),
                .a_vout(a_hv[i][j+1]),
                .b_out (b_v [i+1][j]),
                .b_vout(b_vv[i+1][j]),
                .acc   (acc[i][j])
            );
        end
    end

endmodule
