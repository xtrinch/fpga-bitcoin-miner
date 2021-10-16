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

	uart_comm comm (
		.sys_clk (CLK),
		.rx_serial (RX),
		.tx_serial (TX),
        .error_led (D5),
        .status_led1 (D1),
        .status_led2 (D2),
        .status_led3 (D3),
        .status_led4 (D4)
	);

endmodule