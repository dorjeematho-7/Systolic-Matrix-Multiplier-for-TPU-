// Processing element for an output-stationary systolic array.
// A moves west->east, B moves north->south, each delayed by one register.
// The accumulator updates only when both incoming operands are valid.
module pe #(
    parameter int DW = 8, // operand width (signed)
    parameter int AW = 17 // accumulator width (signed)
) (
    input logic clk,
    input logic rst_n,
    input logic clear, // synchronous accumulator clear
    input logic signed [DW-1:0] a_in,
    input logic a_vin,
    input logic signed [DW-1:0] b_in,
    input logic b_vin,
    output logic signed [DW-1:0] a_out,
    output logic a_vout,
    output logic signed [DW-1:0] b_out,
    output logic b_vout,
    output logic signed [AW-1:0] acc
);

    logic signed [2*DW-1:0] prod;
    assign prod = a_in * b_in;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_out  <= '0;
            a_vout <= 1'b0;
            b_out  <= '0;
            b_vout <= 1'b0;
            acc    <= '0;
        end else begin
            a_out  <= a_in;
            a_vout <= a_vin;
            b_out  <= b_in;
            b_vout <= b_vin;
            if (clear)
                acc <= '0;
            else if (a_vin && b_vin)
                acc <= acc + prod;
        end
    end

endmodule
