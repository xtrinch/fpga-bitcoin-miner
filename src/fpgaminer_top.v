`timescale 1ns/1ps

module fpgaminer_top (
    input wire hash_clk,
	input wire [255:0] midstate_vw,
	input wire [95:0] work_data,
	input wire [31:0] nonce_min, // minimum nonce for job
	input wire [31:0] nonce_max, // maximum nonce for job
	input wire reset,
	output reg [31:0] golden_nonce = 0,
	output reg new_golden_nonce = 1'b0 // whether we found a hash
);
	// determines how unrolled the SHA-256 calculations are. 
    // a setting of 0 will completely unroll the calculations, 
    // resulting in 128 rounds (two hashes, each 64 rounds) and a large, fast design, 
    // a setting of 1 will result in 64 rounds, with half the size and
	// half the speed. 2 will be 32 rounds, with 1/4th the size and speed.
	// Valid range: [0, 5]
	parameter LOOP_LOG2 = 5;

	// to make sure we always get exponents of number two;
    // values can be 1, 2, 4, 8, 16, 32
	localparam [5:0] LOOP = (6'd1 << LOOP_LOG2);

	// The nonce will always be larger at the time we discover a valid
	// hash. This is its offset from the nonce that gave rise to the valid
	// hash (except when LOOP_LOG2 == 0 or 1, where the offset is 131 or
	// 66 respectively).
	localparam [31:0] GOLDEN_NONCE_OFFSET = (32'd1 << (7 - LOOP_LOG2)) + 32'd1;

	reg [511:0] data = 0; // a block header is 640 bits
    reg [31:0] nonce = 32'h00000000;

	wire [255:0] hash; // hash of the 2nd 511 bits of the block header
    wire [255:0] hash2; // hash of the first round of block header hash
	reg [5:0] cnt = 6'd0; // where in the LOOP are we
	reg feedback = 1'b0; // whether we're inside the same hash or a new one
	reg wait_for_work = 1'b1;

	// the hash of the first 511 bits where the header version n' stuff is
    // it is precomputed at the PC and sent to the miner 
	reg [255:0] midstate_buf = 0;
    // the leftmost data of the right 511 bits of the header (a piece of the merkle root, time, target) 
    reg [95:0] data_buf = 0;

    // sha256 stores binary in big endian (lowest address -> most significant value)
    // hash = hashlib.sha256(hashlib.sha256(header_bin).digest()).digest()
    // 1st hash round - rightmost 511 bits of the block header
	sha256_transform #(.LOOP(LOOP)) uut (
		.clk(wait_for_work ? 1'b0 : hash_clk),
		.feedback(feedback),
		.cnt(cnt), // where in the LOOP are we
		.rx_state(midstate_buf),
		.rx_input(data), // data we'd like to hash
		.tx_hash(hash)
	);
    // 2nd hash round - hashing the hash of the first round
	sha256_transform #(.LOOP(LOOP)) uut2 (
		.clk(wait_for_work ? 1'b0 : hash_clk),
		.feedback(feedback),
		.cnt(cnt), // where in the LOOP are we
		.rx_state(256'h5be0cd191f83d9ab9b05688c510e527fa54ff53a3c6ef372bb67ae856a09e667), // initial hash values h7 downto h1
		.rx_input({256'h0000010000000000000000000000000000000000000000000000000080000000, hash}), // 256bits of padding (length on the left and 1 padded on the right) + previous hash
		.tx_hash(hash2)
	);

	//// Control Unit
	reg feedback_d1 = 1'b1; // value of feedback 2 cycles back (this means the hash from the previous cycle is valid)
	reg golden_nonce_found = 1'b0; // output is delayed for 1 cycle behind internal value
	wire [5:0] cnt_next;
	wire [31:0] nonce_next;
	wire feedback_next;

    // from 0 to LOOP - 1
	assign cnt_next =  (LOOP == 1) ? 6'd0 : (cnt + 6'd1) & (LOOP-1);

	// On the first count (cnt==0), load data from previous stage (no feedback)
	// on 1..LOOP-1, take feedback from current stage
	// This reduces the throughput by a factor of (LOOP), but also reduces the design size by the same amount
    // {(LOOP_LOG2){1'b0}} === 0 replicated LOOP_LOG2 times
	assign feedback_next = (LOOP == 1) ? 1'b0 : (cnt_next != {(LOOP_LOG2){1'b0}});

    // if we're inside the feedback loop, do not increment the nonce
	assign nonce_next = reset ? nonce_min : feedback_next ? nonce : (nonce + 32'd1);
	
	always @ (posedge hash_clk)
	begin
		if (reset)
			wait_for_work <= 1'b0;

        // Give new data to the hasher, feed it the hash of the first 511 bits of the block header
        midstate_buf <= midstate_vw;
        data_buf <= work_data;
		
		cnt <= cnt_next;
		feedback <= feedback_next;
		feedback_d1 <= feedback;
		new_golden_nonce <= golden_nonce_found; // output is delayed by one cycle to make sure the nonce is written into golden_nonce

        // { padding length=384 bits, nonce, data=12 bytes }
        // 0x00000280 = 640
        // 0x80000000 = 100... in binary - padded 1
		data <= {384'h000002800000000000000000000000000000000000000000000000000000000000000000000000000000000080000000, nonce_next, data_buf[95:0]};
		nonce <= nonce_next;

		// Check to see if the last hash generated is valid.
		golden_nonce_found <= (hash2[255:224] == 32'h00000000) && !feedback_d1;
		if(golden_nonce_found)
		begin
			wait_for_work <= 1'b1;
			case (LOOP)
				1: begin 
					golden_nonce <= nonce - 32'd131;
					$display ("golden nonce found: %8x\n", nonce - 32'd131);
				end
				2: begin 
					golden_nonce <= nonce - 32'd66;
					$display ("golden nonce found: %8x\n", nonce - 32'd66);
				end
				default: begin
					golden_nonce <= nonce - GOLDEN_NONCE_OFFSET;
					$display ("golden nonce found: %8x\n", nonce - GOLDEN_NONCE_OFFSET);
				end
			endcase;
		end

		`ifdef SIM
		if (!feedback_d1 && !wait_for_work)
			$display ("nonce: %8x\nhash2: %64x\n", nonce, hash2);
		`endif
	end
endmodule