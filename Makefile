# Project setup
BUILD     = ./build
DEVICE    = 8k
FOOTPRINT = ct256
NAME = miner

# Files
FILES = src/fpgaminer_top.v src/sha256_functions.v src/sha256_transform.v src/top.v src/uart.v src/uart_comm.v src/main_pll.v

.PHONY: all clean burn

all:
	# clean old build data
	rm $(BUILD)/*
	
	# if build folder doesn't exist, create it
	mkdir -p $(BUILD)
	
	# synthesize using Yosys
	yosys -p "synth_ice40 -top top -json $(BUILD)/$(NAME).json" $(FILES) -v 5 -l $(BUILD)/$(NAME)-yosys.log

	# Place and route using nextpnr
	nextpnr-ice40 --quiet --hx8k --package tq144:4k --json $(BUILD)/$(NAME).json --pcf src/icestick.pcf --asc $(BUILD)/$(NAME).asc --log $(BUILD)/$(NAME)-nextpnr.log

	# Convert to bitstream using IcePack
	icepack $(BUILD)/$(NAME).asc $(BUILD)/$(NAME).bin

test-miner:
	iverilog -o ./testbenches/test-miner.sim ./testbenches/test_fpgaminer_top.v ./src/fpgaminer_top.v ./src/sha256_transform.v ./src/sha256_functions.v
	./testbenches/test-miner.sim

test-uart:
	iverilog -o ./testbenches/test-uart.sim ./testbenches/test_uart_comm.v ./src/uart_comm.v ./src/uart.v
	./testbenches/test-uart.sim

test-top:
	iverilog -o ./testbenches/test-top.sim ./testbenches/test_top.v ./testbenches/mock_pll.v ./src/uart_comm.v ./src/uart.v ./src/fpgaminer_top.v ./src/sha256_transform.v ./src/sha256_functions.v ./src/top.v
	./testbenches/test-top.sim

burn:
	iceprog $(BUILD)/$(NAME).bin

clean:
	rm build/*