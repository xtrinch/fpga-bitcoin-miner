
// tx_data:		Work data.
//
// sys_clk:	16x the desired UART baud rate.
// rx_serial:	UART RX (incoming)
// tx_serial:	UART TX (outgoing)

// Implemented incoming messages:
// PING, GET_INFO
//
// Implemented outgoing messages:
// PONG, INFO, INVALID

module uart_comm (
	input wire sys_clk, // UART clock domain
	input wire hash_clk, // hash clock domain
	input wire rx_serial,
	input wire [31:0] golden_nonce,
	input wire is_golden_ticket, // whether we found a hash
	output wire tx_serial,
    output wire error_led, // error led
    output wire status_led1,
    output wire status_led2,
    output wire status_led3,
    output wire status_led4,
	output reg [95:0] tx_data = 96'd0, // 12 bytes of the rightmost 511 bits of the header (time, merkleroot, difficulty)
	output reg [31:0] tx_nonce_min = 32'd0, // minimum nonce for job
	output reg [31:0] tx_nonce_max = 32'd0, // maximum nonce for job
	output reg [255:0] tx_midstate = 256'd0, // midstate hash, hash of the leftmost 511 bits
	output reg tx_new_work = 1'b0, // Indicate new work on midstate, data.
);
	// States
	localparam STATE_IDLE = 3'b001;
	localparam STATE_READ = 3'b010;
	localparam STATE_PARSE = 3'b100;

	// 52 is job size + 8 for message header
	localparam MSG_BUF_LEN = 60;

	// Message Types
	localparam MSG_INFO = 0;
	localparam MSG_INVALID = 1;
	localparam MSG_PUSH_JOB = 2;
	localparam MSG_NONCE = 3;
	localparam MSG_ACK = 4;

	// 256 bits midstate hash, 96 bits time+merkleroot+difficulty, 32 bits min nonce, 32 bits max nonce
	localparam JOB_SIZE = 256 + 96 + 32 + 32;

	reg [JOB_SIZE-1:0] current_job = {JOB_SIZE{1'b0}};
	reg new_work_flag = 1'b0;

	reg [63:0] system_info = 64'hDEADBEEF13370D13;

	wire reset = 0;
	reg transmit; // signal to start transmitting byte
    reg transmit_packet; // signal to start transmitting packet
	reg [7:0] tx_byte;
	wire received; // signal that a byte has been received
	wire [7:0] rx_byte;
	wire is_receiving; // whether uart is receiving or not
	wire is_transmitting; // whether uart is transmitting or not
	wire recv_error;

	// RX Message Buffer
	reg [63:0] outgoing_msg;
	reg [7:0] outgoing_msg_type;
	reg [MSG_BUF_LEN*8-1:0] msg_data;
	reg [7:0] msg_length; // how long the received message is
    reg [7:0] length; // where in the message are we
    reg [7:0] msg_type; // the type of received message
	reg [3:0] state = STATE_IDLE;

	// assign {status_led4, status_led3, status_led2, status_led1} = rx_byte[3:0];

	assign error_led = recv_error;

	uart #(
		.baud_rate(9600),                 // The baud rate in kilobits/s
		.sys_clk_freq(12000000)           // The master clock frequency
	)
	uart0(
		.clk(sys_clk),                    // The master clock for this module
		.rst(reset),                      // Synchronous reset
		.rx(rx_serial),                   // Incoming serial line
		.tx(tx_serial),                   // Outgoing serial line
		.transmit(transmit),              // Signal to transmit
		.tx_byte(tx_byte),                // Byte to transmit
		.received(received),              // Indicated that a byte has been received
		.rx_byte(rx_byte),                // Byte received
		.is_receiving(is_receiving),      // Low when receive line is idle
		.is_transmitting(is_transmitting),// Low when transmit line is idle
		.recv_error(recv_error)           // Indicates error in receiving packet.
	);

	always @(posedge sys_clk) begin
        case (state)
        	// Waiting for new packet
			STATE_IDLE:
            if (received) begin
                if (rx_byte == 0) begin // ping received, send pong
                    length <= 8'd1;
                    msg_length <= 8'h1;
                    transmit_packet <= 1; // TODO: do with ack
                end
                else if (rx_byte < 8) begin	// Invalid Length, 8 bytes is the smallest, send message invalid
                    length <= 8'd1;
                    msg_length <= 8'h8;
                    msg_type <= MSG_INVALID;
                    transmit_packet <= 1;
                end
                else begin // received a valid length, continue to read
                    length <= 8'd2; // starts at two because the first one is the packet length
                    msg_length <= rx_byte;
                    state <= STATE_READ;
                end
            end
			else if (meta_is_golden_ticket) begin
				length <= 8'd1;
				msg_length <= 8'h12; // 8 header + 4 for nonce
				msg_data <= meta_golden_nonce;
				transmit_packet <= 1;
				msg_type <= MSG_NONCE;
				meta_is_golden_ticket <= 0;
			end

			// Reading packet into msg_data
			STATE_READ: 
            if (received) begin
				msg_data <= {rx_byte, msg_data[MSG_BUF_LEN*8-1:8]}; // shift right by 8 bits and put in the new received byte
				length <= length + 8'd1;

				if (length == 8'd4) // when at 4th byte, we're at message type
					msg_type <= rx_byte;

				if (length == msg_length) // finished, parse the packet
					state <= STATE_PARSE;
			end

			// Parse packet
			STATE_PARSE: 
            if (!transmit_packet) begin // if we're still transmitting a packet, wait
				// By default, we'll send some kind of
				// response. Special cases are handled below.
				length <= 8'd1;
				msg_length <= 8'd8;
				state <= STATE_IDLE;
                transmit_packet <= 1;

				if (msg_type == MSG_INFO && msg_length == 8) begin // header length always 8
					msg_type <= MSG_INFO;
					msg_data <= system_info;
					msg_length <= 8'd16;
				end
				else if (msg_type == MSG_PUSH_JOB && msg_length == (JOB_SIZE/8 + 8)) // job size + 8 byte header
				begin
					current_job <= msg_data[MSG_BUF_LEN*8-32-1:MSG_BUF_LEN*8-32-JOB_SIZE]; // header is in the beginning, so the job is on the left
					new_work_flag <= ~new_work_flag;

					msg_type <= MSG_ACK;
				end
				else
					msg_type <= MSG_INVALID;
			end
        endcase

        // transmits the actual packet, decoupled from the state
        // machine as to not block the receives
        transmit <= 1'b0;  
        if (transmit_packet && !is_transmitting) begin
            transmit <= 1'b1;
            length <= length + 8'd1;

            if (length == 8'd1)
                tx_byte <= msg_length;
            else if (length == 8'd2 || length == 8'd3)
                tx_byte <= 8'h00;
            else if (length == 8'd4)
                tx_byte <= msg_type;
            else if (length <= msg_length)
            begin
                tx_byte <= msg_data[((MSG_BUF_LEN*8)-1):((MSG_BUF_LEN-1)*8)]; 
				msg_data <= msg_data << 8;
            end

            if (length == msg_length)
                transmit_packet <= 0;
        end
    end

	// Cross from comm_clk to hash_clk
	reg [JOB_SIZE-1:0] meta_job;
	reg [2:0] meta_new_work_flag;
	reg meta_is_golden_ticket;
	reg [31:0] meta_golden_nonce;

	always @ (posedge hash_clk)
	begin
		meta_job <= current_job;
		meta_new_work_flag <= {new_work_flag, meta_new_work_flag[2:1]}; // right shift

		tx_new_work <= meta_new_work_flag[2] ^ meta_new_work_flag[1]; // why then three, if we only check the first two?
		{tx_midstate, tx_data, tx_nonce_min, tx_nonce_max} <= meta_job;

		if (is_golden_ticket) begin
			// do something
			meta_is_golden_ticket <= 1;
			meta_golden_nonce <= golden_nonce;
		end
	end
endmodule