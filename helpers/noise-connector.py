#!/usr/bin/env python3

# source: https://github.com/jakubtrnka/braiins-open/blob/master/protocols/stratum/python_noise_tcp_client/requirements.txt

import socket
import binascii
import base58
import ed25519
import time

from dissononce.processing.handshakepatterns.interactive.NX import NXHandshakePattern
from dissononce.processing.impl.handshakestate import HandshakeState
from dissononce.processing.impl.symmetricstate import SymmetricState
from dissononce.processing.impl.cipherstate import CipherState
from dissononce.cipher.chachapoly import ChaChaPolyCipher
from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.hash.blake2s import Blake2sHash

HOST = "v2.eu.stratum.slushpool.com"
PORT = 3336
SLUSHPOOL_CA_PUBKEY = "u95GEReVMjK6k5YqiSFNqqTnKU4ypU2Wm8awa6tmbmDmk1bWt"


class SignatureMessage:
    def __init__(self, raw_signature: bytes, noise_static_pubkey: bytes):
        self.authority_key = base58.b58decode_check(SLUSHPOOL_CA_PUBKEY)
        self.noise_static_pubkey = noise_static_pubkey
        self.version = int.from_bytes(raw_signature[0:2], byteorder="little")
        self.valid_from = int.from_bytes(raw_signature[2:6], byteorder="little")
        self.not_valid_after = int.from_bytes(raw_signature[6:10], byteorder="little")
        signature_length = int.from_bytes(raw_signature[10:12], byteorder="little")
        self.signature = bytes(raw_signature[12 : 12 + signature_length])

    def __serialize_for_verification(self):
        buffer = self.version.to_bytes(2, byteorder="little")
        buffer += self.valid_from.to_bytes(4, byteorder="little")
        buffer += self.not_valid_after.to_bytes(4, byteorder="little")
        buffer += len(self.noise_static_pubkey).to_bytes(2, byteorder="little")
        buffer += self.noise_static_pubkey
        buffer += len(self.authority_key).to_bytes(2, byteorder="little")
        buffer += self.authority_key
        return bytes(buffer)

    def verify(self):
        pool_pubkey = ed25519.VerifyingKey(self.authority_key)
        message = self.__serialize_for_verification()
        pool_pubkey.verify(self.signature, message)
        assert int(time.time()) < self.not_valid_after, "Expired certificate"


def wrap(item: bytes) -> bytes:
    item_length = len(item)
    return item_length.to_bytes(2, byteorder="little") + item


def unwrap(item: bytes) -> (bytes, bytes):
    length_prefix = item[0:2]
    payload_length = int.from_bytes(length_prefix, byteorder="little")
    return (item[2 : 2 + payload_length], item[payload_length + 2 :])


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Connecting to ", HOST, " port ", PORT)
    sock.connect((HOST, PORT))
    print("Connected.")

    # prepare handshakestate objects for initiator and responder
    our_handshakestate = HandshakeState(
        SymmetricState(
            CipherState(
                # AESGCMCipher()
                ChaChaPolyCipher()  # chacha20poly1305
            ),
            Blake2sHash(),
        ),
        X25519DH(),
    )

    our_handshakestate.initialize(NXHandshakePattern(), True, b"")

    # -> e     which is really      -> 2 byte length, 32 byte public key, 22 byte cleartext payload
    message_buffer = bytearray()
    our_handshakestate.write_message(b"", message_buffer)
    message_buffer = wrap(bytes(message_buffer))
    num_sent = sock.send(message_buffer)  # rpc send

    #  <- e, ee, s, es, SIGNATURE_NOISE_MESSAGE
    message_buffer = bytearray()
    ciphertext = sock.recv(4096)  # rpc recv
    frame, _ = unwrap(ciphertext)
    our_handshakestate.read_message(frame, message_buffer)

    pool_static_server_key = our_handshakestate.rs.data

    signature = SignatureMessage(message_buffer, pool_static_server_key)
    signature.verify()

    print(
        "Noise encrypted connection established successfuly. Nothing to do now, Closing..."
    )


if __name__ == "__main__":
    main()