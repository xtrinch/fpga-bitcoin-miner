# ICEStick UART + packets encoding / decoding

Example UART project for **Lattice icestick** FPGA board. Supports `PING` & `GET_INFO` requests from master (in our case the linux PC).

Actual low level UART module is courtesy of https://github.com/cyrozap/osdvu.

Built with PlatformIO.

## Usage

Build with `pio run` upload with `pio run --target upload`.

Compile C code with `gcc pc-comm.c -o pc-comm`  and run with `./pc-comm` to observe serial packets.

Send packets to FPGA with bash command:
  - Get info: `echo -en '\x08\x00\x00\x00\x00\x00\x00\x00' > /dev/ttyUSB2`
  - Ping: `echo -en '\x00' > /dev/ttyUSB2`

Both should return either pong or the info you can find harcoded in the `uart_comm` file:
  - Pong: `0x01`
  - Get info response: `0x10 00 00 00 de ad be ef 13 37 0d 13 00 00 00 00`