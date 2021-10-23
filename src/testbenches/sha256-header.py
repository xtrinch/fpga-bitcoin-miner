# none produce the right hash!

from hashlib import sha256

# big endian
hash = (sha256(sha256(
    bytearray.fromhex(
        "00000001"+
        "4cc2c57c7905fd399965282c87fe259e7da366e035dc087a0000141f00000000"+
        "6427b6492f2b052578fb4bc23655ca4e8b9e2b9b69c88041b2ac8c771571d1be"+
        "4de69593"+
        "1a269421"+
        "7a33330e"
    )).digest()).digest().hex())
print(hash)

# something endian
hash = (sha256(sha256(
    bytearray.fromhex(
        "01000000"+
        "000000001F1400007A08DC35E066A37D9E25FE872C28659939FD05797CC5C24C"+
        "BED17115778CACB24180C8699B2B9E8B4ECA5536C24BFB7825052B2F49B62764"+
        "9395E64D"+
        "2194261A"+
        "0E33337A"
    )).digest()).digest().hex())
print(hash)

# test endian
hash = (sha256(sha256(
    bytearray.fromhex(
        "01000000"+
        "4cc2c57c7905fd399965282c87fe259e7da366e035dc087a0000141f00000000"+
        "6427b6492f2b052578fb4bc23655ca4e8b9e2b9b69c88041b2ac8c771571d1be"+
        "4de69593"+
        "1a269421"+
        "7a33330e"
    )).digest()).digest().hex())
print(hash)

first511Oiriginal = "000000014cc2c57c7905fd399965282c87fe259e7da366e035dc087a0000141f000000006427b6492f2b052578fb4bc23655ca4e8b9e2b9b69c88041b2ac8c77"
first511ByteSwapped = "778CACB24180C8699B2B9E8B4ECA5536C24BFB7825052B2F49B62764000000001F1400007A08DC35E066A37D9E25FE872C28659939FD05797CC5C24C01000000"
second511Original = "1571d1be4de695931a2694217a33330e"
second511ByteSwapped = "0E33337A2194261A9395E64DBED17115"
hash = (sha256(sha256(
    bytearray.fromhex(
        first511Oiriginal + second511ByteSwapped
    )).digest()).digest().hex())
print(hash)

hash = (sha256(sha256(
    bytearray.fromhex(
        "000000014cc2c57c7905fd399965282c87fe259e7da366e035dc087a0000141f000000006427b6492f2b052578fb4bc23655ca4e8b9e2b9b69c88041b2ac8c771571d1be4de695931a2694217a33330e"
    )).digest()).digest().hex())
print(hash)

# genesis block
hash = (sha256(sha256(
    bytearray.fromhex(
        "0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c"
    )).digest()).digest().hex())
print(hash)

hash = (sha256(sha256(
    bytearray.fromhex(
        "7C2BAC1D1D00FFFF495FAB294A5E1E4BAAB89F3A32518A88C31BC87F618F76673E2CC77AB2127B7AFDEDA33B000000000000000000000000000000000000000000000000000000000000000000000001"
    )).digest()).digest().hex())
print(hash)