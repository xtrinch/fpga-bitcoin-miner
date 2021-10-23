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