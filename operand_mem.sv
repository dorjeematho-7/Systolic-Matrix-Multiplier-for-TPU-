// One operand bank (one row of A_mem or one column of B_mem): K entries.
// The write port is for the host. The read side is the K:1 input mux,
// driven by the select line (S0 for A, S1 for B).
module operand_mem #(
    parameter int DW = 8,
    parameter int K = 2,
    parameter int KW = (K > 1) ? $clog2(K) : 1
) (
    input logic clk,
    input logic we,
    input logic [KW-1:0] waddr,
    input logic [DW-1:0] wdata,
    input logic [KW-1:0] sel,
    output logic [DW-1:0] rdata
);

    logic [DW-1:0] mem [K];

    always_ff @(posedge clk) begin
        if (we)
            mem[waddr] <= wdata;
    end

    assign rdata = mem[sel];

endmodule
