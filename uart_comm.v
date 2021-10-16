
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
	output reg [95:0] tx_data = 96'd0,
	input wire sys_clk, // UART clock domain
	input wire rx_serial,
	output wire tx_serial,
    output wire error_led, // error led
    output wire status_led1,
    output wire status_led2,
    output wire status_led3,
    output wire status_led4,
);
	// States
	localparam STATE_IDLE = 3'b001;
	localparam STATE_READ = 3'b010;
	localparam STATE_PARSE = 3'b100;

	localparam MSG_BUF_LEN = 57;

	// Message Types
	localparam MSG_INFO = 0;
	localparam MSG_INVALID = 1;

	reg [63:0] system_info = 256'hDEADBEEF13370D13;

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

	assign {status_led4, status_led3, status_led2, status_led1} = rx_byte[3:0];

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
                if (rx_byte == 0) begin
                    length <= 8'd1;
                    msg_length <= 8'h1;
                    transmit_packet <= 1;
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

			// Reading packet into msg_data
			STATE_READ: 
            if (received) begin
				msg_data <= {rx_byte, msg_data[MSG_BUF_LEN*8-1:8]}; // shift right by 8 bits
				length <= length + 8'd1;

				if (length == 8'd4)
					msg_type <= rx_byte;

				if (length == msg_length)
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

				if (msg_type == MSG_INFO && msg_length == 8) begin
					msg_type <= MSG_INFO;
					msg_data <= system_info;
					msg_length <= 8'd16;
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
                // tx_byte <= msg_data[479:472]; 
                // msg_data <= {msg_data[471:0], 8'd0}; // right shift the data for a byte

                tx_byte <= msg_data[((MSG_BUF_LEN*8)-1):((MSG_BUF_LEN-1)*8)]; 
                msg_data <= {msg_data[(((MSG_BUF_LEN-1)*8)-1):0], 8'd0}; // right shift the data for a byte
            end

            if (length == msg_length)
                transmit_packet <= 0;
        end
    end
endmodule