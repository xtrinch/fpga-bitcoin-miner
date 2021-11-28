# source: https://gist.github.com/thoughtpolice/b1cec8d45f2741c3726c0cc2ac83d7f2
# ecp5pll.py: yosys RPC frontend for generating ECP5 PLL modules on the fly
#
# Copyright (C) 2020      Austin Seipp
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

# usage:
#
#     yosys> connect_rpc -exec python3 ./ecp5pll.py
#     yosys> read_verilog test.v
#     yosys> hierarchy
#
# and uses of the module `ECP5_PLL` in your design will be replaced by uses of
# the ECP5 PLL primitive with the given clock outputs, at the specified
# input/output frequencies. example:
#
#    ECP5_PLL
#      #( .IN_MHZ(25)
#       , .OUT0_MHZ(50)
#       , .OUT1_MHZ(30)
#       , .OUT3_MHZ(100)
#       ) pll
#       ( .clkin(clkin)
#       , .reset(1'b0)
#       , .standby(1'b0)
#       , .locked(locked)
#       , .clkout0(clkout0)
#       , .clkout1(clkout1)
#       , .clkout3(clkout3)
#       );
#
#
# [TODO] (aseipp):
#   - phase settings
#   - help message?
#   - tighten up error handling

import json, sys, subprocess

def onoes(s):
    print(json.dumps({ "error": s }))

# from https://github.com/YosysHQ/yosys/blob/master/tests/rpc/frontend.py
def map_parameter(parameter):
	if parameter["type"] == "unsigned":
		return int(parameter["value"], 2)
	if parameter["type"] == "signed":
		width = len(parameter["value"])
		value = int(parameter["value"], 2)
		if value & (1 << (width - 1)):
			value = -((1 << width) - value)
		return value
	if parameter["type"] == "string":
		return parameter["value"]
	if parameter["type"] == "real":
		return float(parameter["value"])

def check_output(params, n):
    if f"\\OUT{str(n)}_MHZ" in params:
        return map_parameter(params[f"\\OUT{str(n)}_MHZ"])
    else:
        return None

def ecppll(modname, params):
    out0 = check_output(params, 0)
    out1 = check_output(params, 1)
    out2 = check_output(params, 2)
    out3 = check_output(params, 3)

    if not "\\IN_MHZ" in params:
        onoes(f"IN_MHZ parameter for {modname} must be specified")
        return

    if not out0 and not out1 and not out2 and not out3:
        onoes(f"must specify at least one output PLL clock line")
        return

    infreq = map_parameter(params["\\IN_MHZ"])

    clkargs = [ "--clkin", str(infreq) ]
    if out0 != None: clkargs = clkargs + [ "--clkout0", str(out0) ]
    if out1 != None: clkargs = clkargs + [ "--clkout1", str(out1) ]
    if out2 != None: clkargs = clkargs + [ "--clkout2", str(out2) ]
    if out3 != None: clkargs = clkargs + [ "--clkout3", str(out3) ]

    cmd = [
        "ecppll",
        "-f", "/dev/stderr",
        "--reset", "--standby"
    ] + clkargs
    # sys.stderr.write(json.dumps(cmd))

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, stderr = proc.communicate()
    pll_module = stderr.decode('utf-8')

    params = ""
    ports0 = ""
    ports1 = ""

    for (n, x) in [ (0, out0), (1, out1), (2, out2), (3, out3) ]:
        if x != None:
            name = "clkout" + str(n)
            params = params + "\n   , parameter OUT" + str(n) + "_MHZ = " + str(x)
            ports0 = ports0 + "\n   , output " + name
            ports1 = ports1 + "\n    , ." + name + "(" + name + ")"

    return pll_module + f"""
module {modname}
  #( parameter IN_MHZ = {str(infreq)}
{params}
   )
   ( input clkin
   , input reset
   , input standby
   , output locked
{ports0}
   );
  pll pllinst
    ( .clkin(clkin)
    , .reset(reset)
    , .locked(locked)
    , .standby(standby)
{ports1}
    );
endmodule
"""

def derive(obj, cmdname):
    if not "module" in obj:
        onoes("invalid derive call (no 'module' key)")
        return

    modname = obj["module"]
    if cmdname != modname:
        raise Exception("ERROR: cmdname and modname should be the same!")

    if not "parameters" in obj:
        onoes("invalid derive call (no 'parameters' key)")
        return

    params = obj["parameters"]
    source = ecppll(modname, params)

    if False: # [NOTE] (aseipp): debugging
        sys.stderr.write(json.dumps(params))
        sys.stderr.write(source)

    print(json.dumps({ "frontend": "verilog", "source": source }))

def main(modname):
    while True:
        line = sys.stdin.readline()
        if not line: break
        obj = json.loads(line)

        if not "method" in obj:
            print(json.dumps({ "error": "invalid input line given (no 'method' key)" }))
        elif obj["method"] == "modules":
            print(json.dumps({ "modules": [ modname ] }))
        elif obj["method"] == "derive":
            derive(obj, modname)
        else:
            print(json.dumps({ "error": "'{}' is not a valid method".format(obj["method"]) }))

        sys.stdout.flush()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        modname = sys.argv[1]
    else:
        modname = "ECP5_PLL"
    main(modname)