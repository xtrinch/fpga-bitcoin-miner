`timescale 1ns/1ps

// mock PLL that should trigger every 1 time delay
module pll(								
	input  clock_in,						
	output clock_out,						
	output locked = 1'b0					
);		
	reg new_clock = 1'b0;				
	assign clock_out = new_clock;		
									
	initial begin
		while(1) #3 new_clock = ~new_clock;
	end
endmodule	