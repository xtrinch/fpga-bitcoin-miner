/**																
 *									
 * Given input frequency:        12.000 MHz				
 * Requested output frequency:  100.000 MHz				
 * Achieved output frequency:   100.500 MHz				
 */									
									
module pll(								
	input  clock_in,						
	output clock_out,						
	output locked // will go high when PLL is locked - has a stable voltage						
);								
									
    ECP5_PLL
    #( .IN_MHZ(12)
     , .OUT0_MHZ(50)
     ) pll
     ( .clkin(clock_in)
     , .reset(1'b0)
     , .standby(1'b0)
     , .locked(locked)
     , .clkout0(clock_out)
     );

endmodule	
