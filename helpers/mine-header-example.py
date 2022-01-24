"""
raw
536870916
b'\xd0\xdf\xbfN`\xbf\x1a-Lj\x1eA\x8bFM\xe5\xe5\x07\xe3\x0fT\xf2\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00'
b'&\xa6\xb9\xceg\xcf\x85S\xc1;\xb79\xe4\xf9\x95\xb8\xf4e4\x10_\xa0\x99\xce\xc0\xdb\x80E)W\x7f\x96'
1643024397
386568320
0
convs
b' \x00\x00\x04'
b'\xd0\xdf\xbfN`\xbf\x1a-Lj\x1eA\x8bFM\xe5\xe5\x07\xe3\x0fT\xf2\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00'
b'&\xa6\xb9\xceg\xcf\x85S\xc1;\xb79\xe4\xf9\x95\xb8\xf4e4\x10_\xa0\x99\xce\xc0\xdb\x80E)W\x7f\x96'
b'a\xee\x90\r'
b'\x17\n\x90\x80'
b'\x00\x00\x00\x00'
Target(diff=2097152)
b' \x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xf2T\x0f\xe3\x07\xe5\xe5MF\x8bA\x1ejL-\x1a\xbf`N\xbf\xdf\xd0\x96\x7fW)E\x80\xdb\xc0\xce\x99\xa0_\x104e\xf4\xb8\x95\xf9\xe49\xb7;\xc1S\x85\xcfg\xce\xb9\xa6&a\xee\x90\r\x17\n\x90\x80\x00\x00\x00\x00'
"""

from hashlib import sha256

# https://www.blockchain.com/btc/block/00000000000000000007ed90d289f313c4f19a44438f3c4c55eca1637c4c8702
# https://blockchain.info/rawblock/00000000000000000007ed90d289f313c4f19a44438f3c4c55eca1637c4c8702?format=hex
# previous block: https://www.blockchain.com/btc/block/00000000000000000004f2540fe307e5e54d468b411e6a4c2d1abf604ebfdfd0

# non-byte reversed version as seen on blockchain.com
version = "0000FF3F"

# byte reversed prev hash as seen on blockchain.com
prev_hash = "D0DFBF4E60BF1A2D4C6A1E418B464DE5E507E30F54F204000000000000000000"

# byte reversed merkle root as seen on blockchain.com
merkle_root = "D4A302B04A7742F73BD84676ABADC0FDBF61B828A3588F4B1728FBED574F538F"

# byte reversed ntime as seen on blockchain.com, epoch time is 1643025553, (original convert from decimal is 61EE9491)
ntime = "9194ee61"

# byte reversed nbits as seen on blockchain.com (original convert from decimal is 170A9080)
nbits = "80900A17"

# byte reversed nonce as seen on blockchain.com (original convert from decimal is 729789CF)
nonce = "CF899772"

expected_hash = "00000000000000000007ED90D289F313C4F19A44438F3C4C55ECA1637C4C8702"

header = version + prev_hash + merkle_root + ntime + nbits + nonce
print(header)

hash = sha256(sha256(bytearray.fromhex(header)).digest()).digest().hex()
hash = bytearray.fromhex(hash)
hash.reverse()
hash = hash.hex().upper()

print("Calculated hash:")
print(hash)
print("Expected hash:")
print(expected_hash)


assert hash == expected_hash
