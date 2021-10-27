/**									
 * PLL configuration							
 *									
 * This Verilog module was generated automatically			
 * using the icepll tool from the IceStorm project.			
 * Use at your own risk.						
 * 									
 * Subsequent tweaks to use a Global buffer were made			
 * by hand.								
 *									
 * Given input frequency:        12.000 MHz				
 * Requested output frequency:  100.000 MHz				
 * Achieved output frequency:   100.500 MHz				
 */									
									
module pll(								
	input  clock_in,						
	output global_clock,						
	output locked							
	);		

	reg new_clock = 1'b0;				
	assign global_clock = new_clock;		
									
	initial while(1) #1 new_clock = ~new_clock;

endmodule	