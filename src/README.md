# ICEStick FPGA LED example project

Example UART project for Lattice icestick FPGA board. Supports PING & GET_INFO requests from master.

Actual low level UART module is courtesy of https://github.com/cyrozap/osdvu.

Built with apio (https://github.com/FPGAwars/apio).

Build with `apio build`, run simulation with `apio sim`, upload with `apio upload`.

Compile C code with `gcc pc-comm.c -o pc-comm` to observe serial packets.

Send packets to FPGA with bash command:
  - Get info: `echo -en '\x08\x00\x00\x00\x00\x00\x00\x00' > /dev/ttyUSB2`
  - Ping: `echo -en '\x00' > /dev/ttyUSB2`

Both should return either pong or the info you can find harcoded in the `uart_comm` file.