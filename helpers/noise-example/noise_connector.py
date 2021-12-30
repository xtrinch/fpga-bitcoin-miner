#!/usr/bin/env python3

# source: https://github.com/jakubtrnka/braiins-open/blob/master/protocols/stratum/python_noise_tcp_client/requirements.txt
# connects to a stratum v2 server, does the noise handshake and then disconnects

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

from protocol_types import U8, U16, U32, STR0_255, U24, BYTES

HOST = "v2.eu.stratum.slushpool.com"
PORT = 3336
SLUSHPOOL_CA_PUBKEY = "u95GEReVMjK6k5YqiSFNqqTnKU4ypU2Wm8awa6tmbmDmk1bWt"


def Frame(extension_type, msg_type_name, payload):
    msg_type_list = {"SetupConnection":[0x00,0],
                     "SetupConnectionSuccess":[0x01,0],
                     "SetupConnectionError":[0x02,0],
                     "ChannelEndpointChanged":[0x03,1],
                     "OpenStandardMiningChannel":[0x10,0],
                     "OpenStandardMiningChannelSuccess":[0x11,0],
                     "OpenStandardMiningChannelError":[0x12,0],
                     "OpenExtendedMiningChannel":[0x13,0],
                     "OpenExtendedMiningChannelSuccess":[0x14,0],
                     "OpenExtendedMiningChannelError":[0x15,0],
                     "UpdateChannel":[0x16,1],
                     "UpdateChannelError":[0x17,1],
                     "CloseChannel":[0x18,1],
                     "SetExtranoncePrefix":[0x19,1],
                     "SubmitSharesStandard":[0x1a,1],
                     "SubmitSharesExtended":[0x1b,1],
                     "SubmitSharesSuccess":[0x1c,1],
                     "SubmitSharesError":[0x1d,1],
                     "NewMiningJob":[0x1e,1],
                     "NewExtendedMiningJob":[0x1f,1],
                     "SetNewPrevHash":[0x20,1],
                     "SetTarget":[0x21,1],
                     "SetCustomMiningJob":[0x22,0],
                     "SetCustomMiningJobSuccess":[0x23,0],
                     "SetCustomMiningJobError":[0x24,0],
                     "Reconnect":[0x25,0],
                     "SetGroupChannel":[0x26,0],
                     "AllocateMiningJobToken":[0x50,0],
                     "AllocateMiningJobTokenSuccess":[0x51,0],
                     "AllocateMiningJobTokenError":[0x52,0],
                     "IdentifyTransactions":[0x53,0],
                     "IdentifyTransactionsSuccess":[0x54,0],
                     "ProvideMissingTransactions":[0x55,0],
                     "ProvideMissingTransactionsSuccess":[0x56,0],
                     "CoinbaseOutputDataSize":[0x70,0],
                     "NewTemplate":[0x71,0],
                     "SetNewPrevHashTDP":[0x72,0],
                     "RequestTransactionData":[0x73,0],
                     "RequestTransactionDataSuccess":[0x74,0],
                     "RequestTransactionDataError":[0x75,0],
                     "SubmitSolution":[0x76,0]

                     }
    msg_type_pair = msg_type_list[msg_type_name]

    msg_type = msg_type_pair[0]

    channel_msg_bit = msg_type_pair[1]

    assert (channel_msg_bit == 0 or channel_msg_bit == 1)
    if channel_msg_bit == 1:
        channel_msg_bit = 0b10000000

    extension_type = extension_type |  channel_msg_bit

    msg_length = payload.__len__()

    return U16(extension_type)+U8(msg_type)+U24(msg_length)+BYTES(payload)

class SetupConnection():
    def __init__(
        self,
        protocol: int,
        max_version: int,
        min_version: int,
        flags: int,
        endpoint_host: str,
        endpoint_port: int,
        vendor: str,
        hardware_version: str,
        firmware: str,
        device_id: str = '',
    ):
        self.protocol = protocol
        self.max_version = max_version
        self.min_version = min_version
        self.flags = flags
        self.endpoint_host = endpoint_host
        self.endpoint_port = endpoint_port
        self.vendor = vendor
        self.hardware_version = hardware_version
        self.firmware = firmware
        self.device_id = device_id
        super().__init__()
    
    def to_bytes(self):
        protocol = U8(self.protocol)
        min_version = U16(self.min_version)
        max_version = U16(self.max_version)
        flags = U32(self.flags)
        endpoint_host = STR0_255(self.endpoint_host)
        endpoint_port = U16(self.endpoint_port)
        vendor = STR0_255(self.vendor)
        hardware_version = STR0_255((self.hardware_version))
        firmware = STR0_255(self.firmware)
        device_id = STR0_255(self.device_id)

        payload = protocol+min_version+max_version+flags+endpoint_host+endpoint_port+vendor+hardware_version+firmware+device_id
        frame = Frame(0x0, "SetupConnection", payload)

        return frame;

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
    cipherstates = our_handshakestate.read_message(frame, message_buffer)

    pool_static_server_key = our_handshakestate.rs.data

    signature = SignatureMessage(message_buffer, pool_static_server_key)
    signature.verify()
    
    # send SetupConnection message
    setup_connection_message = SetupConnection(
        protocol=0,
        max_version=2,
        min_version=2,
        flags=0,
        endpoint_host=HOST,
        endpoint_port=PORT,
        vendor="some_vendor",
        hardware_version="1",
        firmware="unknown",
        device_id="some_id",
    ).to_bytes()
    ciphertext = cipherstates[0].encrypt_with_ad(b'', setup_connection_message)
    sock.send(wrap(ciphertext))

    # receive SetupConnectionSuccess or SetupConnectionError    
    ciphertext = sock.recv(4096)  # rpc recv
    print("Received SetupConnectionSuccess:")
    print(ciphertext)
    
    print(
        "Noise encrypted connection established successfuly. Nothing to do now, Closing..."
    )


if __name__ == "__main__":
    main()