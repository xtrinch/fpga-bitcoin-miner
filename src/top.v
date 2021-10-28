module top (
	input wire CLK,
	input wire RX,
	output wire TX
);

    parameter baud_rate = 9600;
    parameter sys_clk_freq = 12000000;
    parameter LOOP_LOG2 = 6;


    wire [95:0] work_data; // 12 bytes of the rightmost 511 bits of the header (time, merkleroot, difficulty)
	wire [31:0] nonce_min; // minimum nonce for job
	wire [31:0] nonce_max; // maximum nonce for job
	wire [255:0] midstate; // midstate hash, hash of the leftmost 511 bits
    wire rx_new_work; // Indicate new work on midstate, data.
    wire new_golden_nonce;
    wire [31:0] golden_nonce;

    // PLL to get 100.5MHz clock						
	wire hash_clk;
    wire locked;							
    pll myPLL (.clock_in(CLK), .global_clock(hash_clk), .locked(locked));	

    fpgaminer_top #(
        .LOOP_LOG2(LOOP_LOG2) // 0-5
    ) miner (
        .hash_clk (hash_clk),
        .midstate(midstate),
	    .work_data(work_data),
        .reset(rx_new_work),
        .golden_nonce(golden_nonce),
	    .new_golden_nonce(new_golden_nonce), // whether we found a hash
        .nonce_min(nonce_min), // minimum nonce for job
	    .nonce_max(nonce_max) // maximum nonce for job
    );

	uart_comm #(
        .baud_rate(baud_rate),
        .sys_clk_freq(sys_clk_freq)
    ) comm (
		.comm_clk (CLK),
        .golden_nonce(golden_nonce),
	    .new_golden_nonce(new_golden_nonce), // whether we found a hash
        .hash_clk (hash_clk),
		.rx_serial (RX),
		.tx_serial (TX),
        .work_data(work_data), // 12 bytes of the rightmost 511 bits of the header (time, merkleroot, difficulty)
	    .nonce_min(nonce_min), // minimum nonce for job
	    .nonce_max(nonce_max), // maximum nonce for job
	    .midstate(midstate), // midstate hash, hash of the leftmost 511 bits
	    .new_work(rx_new_work) // Indicate new work on midstate, data.
	);
endmodule