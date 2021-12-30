import random
from abc import ABC, abstractmethod

import numpy as np
import simpy
from hashids import Hashids
import socket
import ed25519
import base58
from dissononce.processing.handshakepatterns.interactive.NX import NXHandshakePattern
from dissononce.processing.impl.handshakestate import HandshakeState
from dissononce.processing.impl.symmetricstate import SymmetricState
from dissononce.processing.impl.cipherstate import CipherState
from dissononce.cipher.chachapoly import ChaChaPolyCipher
from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.hash.blake2s import Blake2sHash
import time

SLUSHPOOL_CA_PUBKEY = "u95GEReVMjK6k5YqiSFNqqTnKU4ypU2Wm8awa6tmbmDmk1bWt"

def gen_uid(env):
    hashids = Hashids()
    return hashids.encode(int(env.now * 16), random.randint(0, 16777216))

class Connection:
    def __init__(self, env, port: str, mean_latency=0.01, latency_stddev_percent=10, pool_host='', pool_port=3336):
        self.uid = gen_uid(env)
        self.env = env
        self.port = port
        self.mean_latency = mean_latency
        self.latency_stddev_percent = latency_stddev_percent
        self.conn_target = None
        self.sock = socket.socket()
        self.pool_host = pool_host
        self.pool_port = pool_port
        self.cipher_state: CipherState = None

    def connect_to(self):
        self.sock.connect((self.pool_host, self.pool_port))

        self.connect_to_noise(self.sock, self.pool_host != 'localhost')

    def disconnect(self):
        # TODO: Review whether to use assert's or RuntimeErrors in simulation
        if self.conn_target is None:
            raise RuntimeError('Not connected')
        self.conn_target.disconnect(self)
        self.conn_target = None

    def is_connected(self):
        return self.conn_target is not None

    def send_msg(self, msg):
        print("send msg")
        ciphertext = self.cipher_state.encrypt_with_ad(b'', msg.to_bytes())
        print(msg.to_bytes())
        print(ciphertext)
        print(type(ciphertext))
        final_message = Connection.wrap(ciphertext)
        # print(final_message)
        if self.conn_target:
            self.conn_target.send(final_message)
        else:
            self.sock.send(final_message)

    def connect_to_noise(self, sock, verify_connection: bool = True):
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
        message_buffer = Connection.wrap(bytes(message_buffer))
        num_sent = sock.send(message_buffer)  # rpc send

        #  <- e, ee, s, es, SIGNATURE_NOISE_MESSAGE
        message_buffer = bytearray()
        ciphertext = sock.recv(4096)  # rpc recv
        frame, _ = Connection.unwrap(ciphertext)
        self.cipherstates = our_handshakestate.read_message(frame, message_buffer)
        self.cipher_state = self.cipherstates[0];
        self.decrypt_cipher_state = self.cipherstates[1]
        print(self.cipherstates)
        print(self.decrypt_cipher_state)

        pool_static_server_key = our_handshakestate.rs.data
        print("Received static key:")
        print(pool_static_server_key)
        
        if (verify_connection):
            signature = SignatureMessage(message_buffer, pool_static_server_key, self.pool_host == 'localhost')
            signature.verify()

        print("Handshake done!")
        return True

    @staticmethod
    # adds 2 byte length
    def wrap(item: bytes) -> bytes:
        item_length = len(item)
        return item_length.to_bytes(2, byteorder="little") + item

    @staticmethod
    # removes 2 byte length
    def unwrap(item: bytes) -> (bytes, bytes):
        length_prefix = item[0:2]
        payload_length = int.from_bytes(length_prefix, byteorder="little")
        return (item[2 : 2 + payload_length], item[payload_length + 2 :])

class SignatureMessage:
    def __init__(self, raw_signature: bytes, noise_static_pubkey: bytes, is_localhost: bool):
        print(raw_signature)
        if not is_localhost:
            self.authority_key = base58.b58decode_check(SLUSHPOOL_CA_PUBKEY)
        else:
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
        print(len(message))
        pool_pubkey.verify(self.signature, message)
        # assert int(time.time()) < self.not_valid_after, "Expired certificate"