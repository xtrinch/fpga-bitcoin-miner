module top (
	input wire CLK,
	input wire RX,
	output wire TX,
    output wire D1,
    output wire D2,
    output wire D3,
    output wire D4,
    output wire D5,
);

    reg [95:0] work_data; // 12 bytes of the rightmost 511 bits of the header (time, merkleroot, difficulty)
	reg [31:0] tx_nonce_min; // minimum nonce for job
	reg [31:0] tx_nonce_max; // maximum nonce for job
	reg [255:0] tx_midstate; // midstate hash, hash of the leftmost 511 bits
    reg rx_new_work; // Indicate new work on midstate, data.
    reg is_golden_ticket;
    reg [31:0] golden_nonce;

    // PLL to get 100.5MHz clock						
	wire hash_clk;
    wire locked;							
    pll myPLL (.clock_in(CLK), .global_clock(hash_clk), .locked(locked));	

    fpgaminer_top miner (
        .hash_clk (hash_clk),
        .midstate_vw(tx_midstate),
	    .work_data(work_data),
        .reset(rx_new_work),
        .golden_nonce(golden_nonce),
	    .is_golden_ticket(is_golden_ticket), // whether we found a hash
        .nonce_min(tx_nonce_min), // minimum nonce for job
	    .nonce_max(tx_nonce_max), // maximum nonce for job
    );

	uart_comm comm (
		.sys_clk (CLK),
        .golden_nonce(golden_nonce),
	    .is_golden_ticket(is_golden_ticket), // whether we found a hash
        .hash_clk (hash_clk),
		.rx_serial (RX),
		.tx_serial (TX),
        // .error_led (D5),
        // .status_led1 (D1),
        // .status_led2 (D2),
        // .status_led3 (D3),
        // .status_led4 (D4),
        .tx_data(work_data), // 12 bytes of the rightmost 511 bits of the header (time, merkleroot, difficulty)
	    .tx_nonce_min(tx_nonce_min), // minimum nonce for job
	    .tx_nonce_max(tx_nonce_max), // maximum nonce for job
	    .tx_midstate(tx_midstate), // midstate hash, hash of the leftmost 511 bits
	    .tx_new_work(rx_new_work), // Indicate new work on midstate, data.
	);
endmodule