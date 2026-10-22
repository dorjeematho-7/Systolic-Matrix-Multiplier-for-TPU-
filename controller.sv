// Sequencer that im thinking of is essentially: LOAD -> COMPUTE -> OUTPUT -> LOAD.
// LOAD: the host or whatever writes A/B. Array is fed zeros. start moves to COMPUTE and
//clears the accumulators on that same cycle.
// COMPUTE: thennn for compute we count runs 0..LAST. While count < K, stream k = count from the
//buffers; after that, feed zeros while the wavefront drains.
//The final k enters at K-1 and needs 2(N-1) more cycles to reach
//PE(N-1,N-1), so LAST = K + 2(N-1) - 1.
// OUTPUT: One cycle with done high, then back to LOAD. The accumulators
//hold C until the next start clears them.

module controller #(
    parameter int N = 3,
    parameter int K = 2,
    parameter int KW = (K > 1) ? $clog2(K) : 1
) (
    input logic clk,
    input logic rst_n,
    input logic start,
    output logic clear,
    output logic [KW-1:0] s0, // A_mem select
    output logic [KW-1:0] s1, // B_mem select
    output logic feed_v, // operand valid at the mux outputs
    output logic busy,
    output logic done
);

    localparam int LAST = K + 2 * (N - 1) - 1;
    localparam int CW = (LAST > 0) ? $clog2(LAST + 1) : 1;

    typedef enum logic [1:0] {LOAD, COMPUTE, OUTPUT} state_t;

    state_t state;
    logic [CW-1:0] count;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= LOAD;
            count <= '0;
        end else begin
            case (state)
                LOAD: if (start) begin
                    state <= COMPUTE;
                    count <= '0;
                end
                COMPUTE: begin
                    if (count == CW'(LAST))
                        state <= OUTPUT;
                    else
                        count <= count + 1'b1;
                end
                OUTPUT: state <= LOAD;
                default: state <= LOAD;
            endcase
        end
    end

    assign clear = (state == LOAD) && start;
    assign busy = (state == COMPUTE);
    assign done = (state == OUTPUT);
    assign feed_v = busy && (int'(count) < K);
    assign s0 = feed_v ? KW'(count) : '0;
    assign s1 = s0;

endmodule
