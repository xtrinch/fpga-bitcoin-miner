# fpga bitcoin miner

Work in progress. Come back later.

## Usage

Manual build with `make`.

Compile C code with `gcc pc-comm.c -o pc-comm`  and run with `./pc-comm` to observe serial packets.

Send packets to FPGA with bash command:
  - Get info: `echo -en '\x08\x00\x00\x00\x00\x00\x00\x00' > /dev/ttyUSB2`
  - Ping: `echo -en '\x00' > /dev/ttyUSB2`

Both should return either pong or the info you can find harcoded in the `uart_comm` file:
  - Pong: `0x01`
  - Get info response: `0x10 00 00 00 de ad be ef 13 37 0d 13 00 00 00 00`

## Manual yosys inspection
- `read -vlog2k src/*.v`
- `proc;`

## Todos

- Block headers are currently byte reversed in blocks of 4 bytes for the miner to work correctly. I suspect this is due to the pool's way of calculating midstate. We should be able to circumvent this when calculating our own midstate hashes with minor modifications of the mining code.
- Difficulty should not be hardcoded. It is also incorrect to check for the leading number of zeroes in a hash, when the blocks are byte reversed in blocks of 4 bytes.
- Finalize tests for UART, write tests for the topmost module.
- CRC for the UART module
- All UART packets to 4 byte headers, 4 bytes on the end are for the CRC!

## Utilization

From optimization level 5 to 0:

Info: 	         ICESTORM_LC: 11877/ 7680   154%
Info: 	        ICESTORM_RAM:     0/   32     0%
Info: 	               SB_IO:     3/  256     1%
Info: 	               SB_GB:     8/    8   100%
Info: 	        ICESTORM_PLL:     1/    2    50%
Info: 	         SB_WARMBOOT:     0/    1     0%

Info: 	         ICESTORM_LC: 19737/ 7680   256%
Info: 	        ICESTORM_RAM:     0/   32     0%
Info: 	               SB_IO:     3/  256     1%
Info: 	               SB_GB:     8/    8   100%
Info: 	        ICESTORM_PLL:     1/    2    50%
Info: 	         SB_WARMBOOT:     0/    1     0%

Info: 	         ICESTORM_LC: 35743/ 7680   465%
Info: 	        ICESTORM_RAM:     0/   32     0%
Info: 	               SB_IO:     3/  256     1%
Info: 	               SB_GB:     8/    8   100%
Info: 	        ICESTORM_PLL:     1/    2    50%
Info: 	         SB_WARMBOOT:     0/    1     0%

Info: 	         ICESTORM_LC: 68064/ 7680   886%
Info: 	        ICESTORM_RAM:     0/   32     0%
Info: 	               SB_IO:     3/  256     1%
Info: 	               SB_GB:     8/    8   100%
Info: 	        ICESTORM_PLL:     1/    2    50%
Info: 	         SB_WARMBOOT:     0/    1     0%

Info: Device utilisation:
Info: 	         ICESTORM_LC: 132953/ 7680  1731%
Info: 	        ICESTORM_RAM:     0/   32     0%
Info: 	               SB_IO:     3/  256     1%
Info: 	               SB_GB:     8/    8   100%
Info: 	        ICESTORM_PLL:     1/    2    50%
Info: 	         SB_WARMBOOT:     0/    1     0%

Info: Device utilisation:
Info: 	         ICESTORM_LC: 261901/ 7680  3410%
Info: 	        ICESTORM_RAM:     0/   32     0%
Info: 	               SB_IO:     3/  256     1%
Info: 	               SB_GB:     8/    8   100%
Info: 	        ICESTORM_PLL:     1/    2    50%
Info: 	         SB_WARMBOOT:     0/    1     0%