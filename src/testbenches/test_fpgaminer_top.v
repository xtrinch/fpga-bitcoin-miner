// Testbench for fpgaminer_top.v
// iverilog -o test test_fpgaminer_top.v ../fpgaminer_top.v ../sha256_transform.v ../sha256_functions.v

`timescale 1ns/1ps

module test_fpgaminer_top ();
	`define SIM 1

	reg clk = 1'b0;
    reg reset = 1'b0;

	fpgaminer_top # (.LOOP_LOG2(0)) uut (
        .hash_clk(clk),
        .midstate_vw(256'h228ea4732a3c9ba860c009cda7252b9161a5e75ec8c582a5f106abb3af41f790),
        .work_data(96'h2194261a9395e64dbed17115),
        .nonce_min(32'h0e33337a - 2), // Minus a little so we can exercise the code a bit
        .reset(reset)
    );

	reg [31:0] cycle = 32'd0;

	initial begin
		clk = 0;
		reset = 1;
		#100

        `ifdef SIM
        $display ("Hi! This is a testbench:)\n");
		`endif
		#5 clk = 1;
		#5 clk = 0;
		reset = 0;
		while(1)
		begin
			#5 clk = 1; #5 clk = 0;
		end
	end

    initial begin
        $display ("SIM is not defined :(\n");
    end

	always @ (posedge clk)
	begin
		cycle <= cycle + 32'd1;
	end

endmodule