# Project setup
BUILD     = ./build
DEVICE    = 8k
FOOTPRINT = ct256
NAME = miner
TRELLIS?=/usr/share/trellis

# Files
FILES = src/fpgaminer_top.v src/sha256_functions.v src/sha256_transform.v src/top.v src/uart.v src/uart_comm.v src/main_pll.v ./src/crc32.v
MINER_TEST_FILES = ./src/fpgaminer_top.v ./src/sha256_transform.v ./src/sha256_functions.v
UART_TEST_FILES = ./src/uart_comm.v ./src/uart.v ./src/crc32.v
TOP_TEST_FILES = ./testbenches/mock_pll.v ./src/uart_comm.v ./src/uart.v ./src/fpgaminer_top.v ./src/sha256_transform.v ./src/sha256_functions.v ./src/top.v ./src/crc32.v

.PHONY: all clean burn

all:
	# clean old build data
	# rm $(BUILD)/*
	
	# if build folder doesn't exist, create it
	mkdir -p $(BUILD)

	# synthesize using Yosys (connect the genpll frontend for the clock PLL & synthesize)
	yosys -p "connect_rpc -exec python3 ./src/ecp5pll.py; synth_ecp5 -noflatten -json $(BUILD)/$(NAME).json -top top" $(FILES)

	# Place and route using nextpnr
	nextpnr-ecp5 --top top --quiet --json $(BUILD)/$(NAME).json --lpf src/ecp5evn.lpf --textcfg $(BUILD)/$(NAME)_out.config --um5g-85k --freq 50 --package CABGA381 --log $(BUILD)/$(NAME)-nextpnr.log

	# Convert to bitstream using EcpPack
	ecppack --svf-rowsize 100000 --svf $(BUILD)/$(NAME).svf $(BUILD)/$(NAME)_out.config $(BUILD)/$(NAME)_out.bit

test-miner:
	iverilog -o ./testbenches/test-miner.sim ./testbenches/test_fpgaminer_top.v $(MINER_TEST_FILES)
	./testbenches/test-miner.sim

test-uart:
	iverilog -o ./testbenches/test-uart.sim ./testbenches/test_uart_comm.v $(UART_TEST_FILES)
	./testbenches/test-uart.sim

test-top:
	iverilog -o ./testbenches/test-top.sim ./testbenches/test_top.v $(TOP_TEST_FILES)
	./testbenches/test-top.sim

program:
	# iceprog $(BUILD)/$(NAME).bin
	openocd -f ${TRELLIS}/misc/openocd/ecp5-evn.cfg -c "transport select jtag; init; svf $<; exit"


clean:
	rm build/*

generate-image:
	yosys -p "read_verilog -formal $(FILES); hierarchy -top top; proc; show -notitle -colors 2 -width -format dot -prefix top top"
	dot -Tpng top.dot > output.png