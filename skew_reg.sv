// Delay line of DEPTH registers for one operand stream (data + valid).
// These are the "D" boxes between the input muxes and the array edge.
// DEPTH = 0 is a straight wire.
module skew_reg #(
    parameter int DW = 8,
    parameter int DEPTH = 1
) (
    input logic clk,
    input logic rst_n,
    input logic [DW-1:0] d_in,
    input logic v_in,
    output logic [DW-1:0] d_out,
    output logic v_out
);

    if (DEPTH == 0) begin : g_wire
        assign d_out = d_in;
        assign v_out = v_in;
    end else begin : g_regs
        logic [DW-1:0] d_q [DEPTH];
        logic v_q [DEPTH];

        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                for (int s = 0; s < DEPTH; s++) begin
                    d_q[s] <= '0;
                    v_q[s] <= 1'b0;
                end
            end else begin
                d_q[0] <= d_in;
                v_q[0] <= v_in;
                for (int s = 1; s < DEPTH; s++) begin
                    d_q[s] <= d_q[s-1];
                    v_q[s] <= v_q[s-1];
                end
            end
        end

        assign d_out = d_q[DEPTH-1];
        assign v_out = v_q[DEPTH-1];
    end

endmodule
