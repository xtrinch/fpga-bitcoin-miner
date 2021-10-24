from hashlib import sha256

# genesis block
hash = (sha256(sha256(
    bytearray.fromhex(
        "0100000000000000000000000000000000000000000000000000000000000000000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a29ab5f49ffff001d1dac2b7c"
    )).digest()).digest().hex())
print(hash)

# block from test_data.txt
hash = (sha256(sha256(
    bytearray.fromhex(
        "010000007CC5C24C39FD05792C2865999E25FE87E066A37D7A08DC351F1400000000000049B6276425052B2FC24BFB784ECA55369B2B9E8B4180C869778CACB2BED171159395E64D2194261A0E33337A"
    )).digest()).digest().hex())
print(hash)