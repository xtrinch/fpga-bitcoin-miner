`timescale 1ns/1ps

// uppercase sigma 0
// ROTR 2
// ROTR 13
// ROTR 22
module e0 (
	input [31:0] x, 
	output [31:0] y
);
	assign y = {x[1:0],x[31:2]} ^ {x[12:0],x[31:13]} ^ {x[21:0],x[31:22]};
endmodule

// uppercase sigma 1
// ROTR 6
// ROTR 11
// ROTR 25
module e1 (x, y);

	input [31:0] x;
	output [31:0] y;

	assign y = {x[5:0],x[31:6]} ^ {x[10:0],x[31:11]} ^ {x[24:0],x[31:25]};

endmodule

// choice
// uses the x bit to choose between the y and z bits,
// chooses the y bit if x=1, and chooses the z bit if x=0.
module ch (x, y, z, o);

	input [31:0] x, y, z;
	output [31:0] o;

	assign o = z ^ (x & (y ^ z));

endmodule

// majority
// returns the majority of the three bits
module maj (x, y, z, o);

	input [31:0] x, y, z;
	output [31:0] o;

	assign o = (x & y) | (z & (x | y));

endmodule

// sigma 0
// ROTR 7
// ROTR 18
// SHR 3
module s0 (x, y);

	input [31:0] x;
	output [31:0] y;

	assign y[31:29] = x[6:4] ^ x[17:15];
	assign y[28:0] = {x[3:0], x[31:7]} ^ {x[14:0],x[31:18]} ^ x[31:3];

endmodule

// sigma 1
// ROTR 17
// ROTR 19
// SHR 10
module s1 (x, y);

	input [31:0] x;
	output [31:0] y;

	assign y[31:22] = x[16:7] ^ x[18:9];
	assign y[21:0] = {x[6:0],x[31:17]} ^ {x[8:0],x[31:19]} ^ x[31:10];

endmodule