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

## Todos

- Block headers are currently byte reversed in blocks of 4 bytes for the miner to work correctly. I suspect this is due to the pool's way of calculating midstate. We should be able to circumvent this when calculating our own midstate hashes with minor modifications of the mining code.
- Difficulty should not be hardcoded. It is also incorrect to check for the leading number of zeroes in a hash, when the blocks are byte reversed in blocks of 4 bytes.
- Finalize tests for UART, write tests for the topmost module.