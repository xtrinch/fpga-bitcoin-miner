# Copyright (C) 2019  Braiins Systems s.r.o.
#
# This file is part of Braiins Open-Source Initiative (BOSI).
#
# BOSI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Please, keep in mind that we may also license BOSI or any part thereof
# under a proprietary license. For more information on the terms and conditions
# of such proprietary license or if you have any other questions, please
# contact us at opensource@braiins.com.
import argparse
import socket
import base64
from itertools import cycle

import numpy as np
import simpy
from colorama import init, Fore
from event_bus import EventBus
import socket

import sim_primitives.coins as coins
import sim_primitives.mining_params as mining_params
from sim_primitives.miner import Miner, MinerV2
from sim_primitives.pool import Pool
from sim_primitives.stratum_v2.pool import PoolV2
from dissononce.processing.handshakepatterns.interactive.NX import NXHandshakePattern
from dissononce.processing.impl.handshakestate import HandshakeState
from dissononce.processing.impl.symmetricstate import SymmetricState
from dissononce.processing.impl.cipherstate import CipherState
from dissononce.cipher.chachapoly import ChaChaPolyCipher
from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.hash.blake2s import Blake2sHash
from cryptography.hazmat.primitives.asymmetric import x25519
from sim_primitives.connection import Connection
from sim_primitives.stratum_v2.messages import SetupConnection, SetupConnectionSuccess

init()
bus = EventBus()

def main():
    np.random.seed(123)
    parser = argparse.ArgumentParser(
        prog='mine.py',
        description='Simulates interaction of a mining pool and two miners',
    )
    parser.add_argument(
        '--realtime',
        help='run simulation in real-time (otherwise is run as fast as possible)',
        action='store_const',
        const=True,
    )
    parser.add_argument(
        '--rt-factor',
        help='real-time simulation factor, default=1 (enter 0.5 to be twice as fast than the real-time',
        type=float,
        default=1,
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='simulation time limit in seconds, default = 500',
        default=50,
    )
    parser.add_argument(
        '--verbose',
        help='display all events (warning: a lot of text is generated)',
        action='store_const',
        const=True,
    )
    parser.add_argument(
        '--latency',
        help='average network latency in seconds, default=0.01',
        type=float,
        default=0.01,
    )
    parser.add_argument(
        '--no-luck', help='do not simulate luck', action='store_const', const=True
    )

    parser.add_argument(
        '--plain-output',
        help='Print just values to terminal: accepted shares, accepted submits,'
        ' stale shares, stale submits, rejected submits',
        action='store_true',
    )

    args = parser.parse_args()
    if args.realtime:
        env = simpy.rt.RealtimeEnvironment(factor=args.rt_factor)
        start_message = '*** starting simulation in real-time mode, factor {}'.format(
            args.rt_factor
        )
    else:
        env = simpy.Environment()
        start_message = '*** starting simulation (running as fast as possible)'

    if args.verbose:
        @bus.on('pool1')
        def subscribe_pool1(ts, conn_uid, message, aux=None):
            print(
                Fore.LIGHTCYAN_EX,
                'T+{0:.3f}:'.format(ts),
                '(pool1)',
                conn_uid if conn_uid is not None else '',
                message,
                aux,
                Fore.RESET,
            )

    pool = Pool(
        'pool1',
        env,
        bus,
        protocol_type=PoolV2,
        default_target=coins.Target.from_difficulty(
            100000, mining_params.diff_1_target
        ),
        enable_vardiff=True,
        simulate_luck=not args.no_luck,
    )

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', 2000))
    sock.listen(1)
    print("Listening for connections")

    conn, addr = sock.accept()
    print('Accepted connection from', addr)

    our_private = base64.b64decode('WAmgVYXkbT2bCtdcDwolI88/iVi/aV3/PHcUBTQSYmo=')
    private = x25519.X25519PrivateKey.from_private_bytes(our_private)

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

    pool_s = X25519DH().generate_keypair()
    print(pool_s.__dict__)
    print(pool_s.public.__dict__)
    print(pool_s.private.__dict__)
    our_handshakestate.initialize(NXHandshakePattern(), False, b"", s=pool_s)

    # wait for empty message receive
    ciphertext = conn.recv(4096)
    frame, _ = Connection.unwrap(ciphertext)
    message_buffer = bytearray()
    our_handshakestate.read_message(frame, message_buffer)

    # when we do, respond
    ## in the buffer, there should be Signature Noise Message, but we 
    ## obviously don't really know how to construct it, so we'll skip it for localhost
    message_buffer = bytearray()
    cipherstates = our_handshakestate.write_message(b"", message_buffer)
    message_buffer = Connection.wrap(bytes(message_buffer))
    num_sent = conn.send(message_buffer)  # rpc send

    print("Handshake done")

    # wait for open connection
    ciphertext = conn.recv(4096)
    print("Raw: Setup connection rcv")
    print(ciphertext)
    frame, _ = Connection.unwrap(ciphertext)
    plaintext = cipherstates[0].decrypt_with_ad(b'', frame)
    print("Decoded: Setup connection rcv")
    print(plaintext)
    
    # plaintext is a frame
    extension_type = plaintext[0:1]
    msg_type = plaintext[2]
    
    if msg_type == 0x00:
        setup_connection_msg = SetupConnection.from_bytes(plaintext[6:]) # 0-6 is general frame data
        pool.protocol_type.visit_setup_connection(setup_connection_msg)
    else:
        raise ValueError('Expected a setup connection')

    env.run(until=args.limit)

    if not args.plain_output:
        print(start_message)

    if args.plain_output:
        print(
            pool.accepted_shares,
            pool.accepted_submits,
            pool.stale_shares,
            pool.stale_submits,
            pool.rejected_submits,
            sep=',',
        )
    else:
        print('simulation finished!')
        print(
            'accepted shares:',
            pool.accepted_shares,
            'accepted submits:',
            pool.accepted_submits,
        )
        print(
            'stale shares:',
            pool.stale_shares,
            'stale submits:',
            pool.stale_submits,
            'rejected submits:',
            pool.rejected_submits,
        )

if __name__ == '__main__':
    main()
