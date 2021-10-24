module top (
	input wire CLK,
	input wire RX,
	output wire TX,
    // output wire D1,
    // output wire D2,
    // output wire D3,
    // output wire D4,
    // output wire D5,
);

    reg [95:0] work_data; // 12 bytes of the rightmost 511 bits of the header (time, merkleroot, difficulty)
	reg [31:0] nonce_min; // minimum nonce for job
	reg [31:0] nonce_max; // maximum nonce for job
	reg [255:0] midstate; // midstate hash, hash of the leftmost 511 bits
    reg rx_new_work; // Indicate new work on midstate, data.
    reg new_golden_ticket;
    reg [31:0] golden_nonce;

    // PLL to get 100.5MHz clock						
	wire hash_clk;
    wire locked;							
    pll myPLL (.clock_in(CLK), .global_clock(hash_clk), .locked(locked));	

    fpgaminer_top #(
        .LOOP_LOG2(5) // 0-5
    ) miner (
        .hash_clk (hash_clk),
        .midstate_vw(midstate),
	    .work_data(work_data),
        .reset(rx_new_work),
        .golden_nonce(golden_nonce),
	    .new_golden_ticket(new_golden_ticket), // whether we found a hash
        .nonce_min(nonce_min), // minimum nonce for job
	    .nonce_max(nonce_max), // maximum nonce for job
    );

	uart_comm #(
        .baud_rate(9600),
        .sys_clk_freq(12000000),
    ) comm (
		.comm_clk (CLK),
        .golden_nonce(golden_nonce),
	    .new_golden_ticket(new_golden_ticket), // whether we found a hash
        .hash_clk (hash_clk),
		.rx_serial (RX),
		.tx_serial (TX),
        // .error_led (D5),
        // .status_led1 (D1),
        // .status_led2 (D2),
        // .status_led3 (D3),
        // .status_led4 (D4),
        .work_data(work_data), // 12 bytes of the rightmost 511 bits of the header (time, merkleroot, difficulty)
	    .nonce_min(nonce_min), // minimum nonce for job
	    .nonce_max(nonce_max), // maximum nonce for job
	    .midstate(midstate), // midstate hash, hash of the leftmost 511 bits
	    .new_work(rx_new_work), // Indicate new work on midstate, data.
	);
endmodule