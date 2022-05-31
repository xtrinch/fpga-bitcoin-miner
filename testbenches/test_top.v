`timescale 1ns/1ps

// the idea of this module is to send job via uart,
// wait for the miner to mine it, and check that it
// has sent the correct golden nonce back via uart

// the example to be mined is the genesis block (see genesis_block.txt)
module test_top ();
	`define SIM 1

	// Clocks
	reg comm_clk = 0;
	initial while(1) #5 comm_clk = ~comm_clk;

    parameter LOOP_LOG2 = 5;

	reg test_passed = 0;

	// UUT
	reg uut_rx = 1'b1;
	wire uut_tx;
	wire [255:0] uut_midstate;
	wire [95:0] uut_data;
	wire [31:0] uut_noncemin, uut_noncemax;

	localparam baud_rate = 1;
	localparam sys_clk_freq = 16; // 160/10

    top #(
		.baud_rate(baud_rate),
		.sys_clk_freq(sys_clk_freq),
        .LOOP_LOG2(LOOP_LOG2)
	) miner (
        .CLK(comm_clk),
        .RX(uut_rx),
        .TX(uut_tx)
    );

	// Test Input Data
	initial
	begin
		#100;
		uart_delay;

		// PING
		uart_send_byte (8'h00);
		uart_delay;

		// GET_INFO
		uart_send_byte (8'h08); // message length
		uart_send_byte (8'h00);
		uart_send_byte (8'h00);
		uart_send_byte (8'h00); // message type
		uart_send_byte (8'hf9); // crc
		uart_send_byte (8'hea); // crc
		uart_send_byte (8'h98); // crc
		uart_send_byte (8'h0a); // crc
		uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay;
		uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay;

		// Bad length
		uart_send_byte (8'h6);
		uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay;
		uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay;

		// INVALID - tell fpga 8 will be sent, then send 7
		uart_send_byte (8'h08); // message length
		uart_send_byte (8'h00);
		uart_send_byte (8'h00);
		uart_send_byte (8'h00); // message type
		uart_send_byte (8'hf9); // crc
		uart_send_byte (8'hea); // crc
		uart_send_byte (8'h98); // crc
		uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay;
		uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay;

		// PUSH_JOB: header, 256 bits midstate hash, 96 bits time+merkleroot+difficulty, 32 bits min nonce, 32 bits max nonce
        // pushed in reverse order
		uart_send_word (32'h0200003C); // byte reversed, ofc, length 60
		uart_send_word (32'hFFFFFFFF); // max nonce
		uart_send_word (32'h1DAC2B7B); // min nonce; fast version - 1DAC2B7B; slow, with response - 1DAC2B00
		uart_send_word (32'h4B1E5E4A); // 2nd part of header FFFF001D 29AB5F49 4B1E5E4A
		uart_send_word (32'h29AB5F49); // 2nd part of header
		uart_send_word (32'hFFFF001D); // 2nd part of header
		uart_send_word (32'hBC909A33); // midstate hash 4719F91B 96B18736 4F0103C8 C3C8D8E9 1E59CAA8 90CCAC7D 6358BFF0 BC909A33
		uart_send_word (32'h6358BFF0); // midstate hash
		uart_send_word (32'h90CCAC7D); // midstate hash
		uart_send_word (32'h1E59CAA8); // midstate hash 
		uart_send_word (32'hC3C8D8E9); // midstate hash
		uart_send_word (32'h4F0103C8); // midstate hash
		uart_send_word (32'h96B18736); // midstate hash
		uart_send_word (32'h4719F91B); // midstate hash
        uart_send_word (32'h814f1577); // crc 77154f81 

		uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay; uart_delay;
		
		#10000;
		if (test_passed)
			$display ("\n*** TEST PASSED ***\n");
		else
			$display ("TEST FAILED: Not enough output data.\n");
		$finish;
	end

	// Test Output Data
	reg tmp;

	initial
	begin
		#100;

		// PONG
		$display ("\nExpecting PONG...");
		uart_expect_byte (8'h01);
		$display ("PASSED: PONG\n");

		// INFO
		$display ("Expecting INFO...");
		uart_expect_byte (8'd16);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'hde);
		uart_expect_byte (8'had);
		uart_expect_byte (8'hbe);
		uart_expect_byte (8'hef);
		uart_expect_byte (8'h13);
		uart_expect_byte (8'h37);
		uart_expect_byte (8'h0d);
		uart_expect_byte (8'h13);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		$display ("PASSED: INFO\n");

		// INVALID
		$display ("Expecting INVALID because the length we sent is too short for any known packet...");
		uart_expect_byte (8'd08);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd01);
		uart_delay; // there's nothing in the next 4 bytes, but they will be received
		uart_delay;
		uart_delay;
		uart_delay;
		$display ("PASSED: INVALID\n");

		// INVALID - tell fpga 8 will be sent, then send 7
		$display ("Expecting INVALID because of not enough packets...");
		uart_expect_byte (8'd08);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd01);
		uart_delay; // there's nothing in the next 4 bytes, but they will be received
		uart_delay;
		uart_delay;
		uart_delay;
		$display ("PASSED: INVALID\n");

		// ACK for push job
		$display ("Expecting ACK for push job...");
        uart_expect_byte (8'h01);
		$display ("PASSED: ACK\n");

		$display ("Expecting MSG_NONCE...");
		// wait for acknowledge of our golden ticket
		uart_expect_byte (8'd8); // not sure, why not just 8?
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd00);
		uart_expect_byte (8'd03); // message type nonce
		uart_expect_byte (8'h1d);
		uart_expect_byte (8'hac);
		uart_expect_byte (8'h2b);
		uart_expect_byte (8'h7c);
		$display ("PASSED: MSG_NONCE\n");

		test_passed = 1;
	end

	// VCD Dump
	initial
	begin
		$dumpfile("uart_comm_tb.vcd");
	end

	// Tasks
	task uart_delay;
	begin
		#1600;
	end
	endtask

    // send one byte via uart, start byte = 0, stop byte = 1
	task uart_send_byte;
	input [7:0] byte;
	begin
		uut_rx = 0;       #160
		uut_rx = byte[0]; #160
		uut_rx = byte[1]; #160;
		uut_rx = byte[2]; #160;
		uut_rx = byte[3]; #160;
		uut_rx = byte[4]; #160;
		uut_rx = byte[5]; #160;
		uut_rx = byte[6]; #160;
		uut_rx = byte[7]; #160;
		uut_rx = 1; #160;
		// Add some timing variance
		while (($random & 3) != 0) #10;
	end
	endtask

    // send one 4 byte word via uart
	task uart_send_word;
	input [31:0] word;
	begin
		uart_send_byte (word[7:0]);
		uart_send_byte (word[15:8]);
		uart_send_byte (word[23:16]);
		uart_send_byte (word[31:24]);
	end
	endtask

	task uart_recv_byte;
	output [7:0] byte;
	begin
		@ (negedge uut_tx);
		#80;
		if (uut_tx)
		begin
			$display ("TEST FAILED: Floating start bit on uut_tx.\n");
			$finish;
		end
		#160 byte[0] = uut_tx;
		#160 byte[1] = uut_tx;
		#160 byte[2] = uut_tx;
		#160 byte[3] = uut_tx;
		#160 byte[4] = uut_tx;
		#160 byte[5] = uut_tx;
		#160 byte[6] = uut_tx;
		#160 byte[7] = uut_tx;
		#160;
		if (~uut_tx)
		begin
			$display ("TEST FAILED: Floating stop bit on uut_tx.\n");
			$finish;
		end
	end
	endtask

	// expect a response on the tx line
	task uart_expect_byte;
	input [7:0] byte;
	reg [7:0] tmp;
	begin
		uart_recv_byte (tmp);

		if (tmp != byte)
		begin
			$display ("TEST FAILED: Expected 0x%02X got 0x%02X.", byte, tmp);
			$finish;
		end
	end
	endtask
endmodule