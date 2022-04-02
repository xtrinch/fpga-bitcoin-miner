// Testbench for fpgaminer_top.v
// run `make test-miner` to compile and run
// see `genesis_block.txt` and `test_data.txt`

`timescale 1ns/1ps

module test_fpgaminer_top ();
	`define SIM 1

	reg clk = 1'b0;
    reg reset = 1'b0;
	wire new_golden_nonce;
	wire [31:0] golden_nonce;

	// setup as it is in test_data.txt
	// fpgaminer_top # (.LOOP_LOG2(0)) uut (
    //     .hash_clk(clk),
    //     .midstate_vw(256'h228ea4732a3c9ba860c009cda7252b9161a5e75ec8c582a5f106abb3af41f790),
    //     .work_data(96'h2194261a9395e64dbed17115),
    //     .nonce_min(32'h0e33337a - 2), // Minus a little so we can exercise the code a bit
    //     .reset(reset)
    // );

	// genesis block; note: the nonce found needs to be byteswapped in blocks of 4 bytes to compare it to blockhain explorer nonce
	fpgaminer_top # (.LOOP_LOG2(0)) uut (
        .hash_clk(clk),
        .midstate(256'h4719F91B96B187364F0103C8C3C8D8E91E59CAA890CCAC7D6358BFF0BC909A33),
        .work_data(96'hFFFF001D29AB5F494B1E5E4A),
        .nonce_min(32'h1DAC2B7C - 2), // Minus a little so we can exercise the code a bit
        .reset(reset),
		.new_golden_nonce(new_golden_nonce),
		.golden_nonce(golden_nonce)
    );

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

	always @ (posedge clk) begin
		if (new_golden_nonce) begin
			if (golden_nonce == 32'h1DAC2B7C)
				$display("Success, nonce is: %8x \n", golden_nonce);
			else
				$display("Tests failed, nonce is: %8x, should be 1dac2b7c\n", golden_nonce);
			$finish;
		end
	end
endmodule