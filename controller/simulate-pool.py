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

import primitives.coins as coins
import primitives.mining_params as mining_params
from primitives.miner import Miner
from primitives.pool import Pool
from dissononce.processing.handshakepatterns.interactive.NX import NXHandshakePattern
from dissononce.processing.impl.handshakestate import HandshakeState
from dissononce.processing.impl.symmetricstate import SymmetricState
from dissononce.processing.impl.cipherstate import CipherState
from dissononce.cipher.chachapoly import ChaChaPolyCipher
from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.hash.blake2s import Blake2sHash
from cryptography.hazmat.primitives.asymmetric import x25519
from primitives.connection import Connection
from primitives.messages import SetupConnection, SetupConnectionSuccess
import asyncio # new module 

init()
bus = EventBus()

def connect():
    np.random.seed(123)
    parser = argparse.ArgumentParser(
        prog='mine.py',
        description='Simulates interaction of a mining pool and two miners',
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
        '--plain-output',
        help='Print just values to terminal: accepted shares, accepted submits,'
        ' stale shares, stale submits, rejected submits',
        action='store_true',
    )

    args = parser.parse_args()

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

    conn1 = Connection(
        'stratum',
        pool_host = 'localhost',
        pool_port = 2000
    )
    
    pool = Pool(
        'pool1',
        bus,
        default_target=coins.Target.from_difficulty(
            100000, mining_params.diff_1_target
        ),
        enable_vardiff=True,
    )

    pool.make_handshake(conn1)

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
    return pool

async def loop(pool: Pool):
    await asyncio.gather(
        pool.receive_loop(),
    )
        
if __name__ == '__main__':
    pool = connect()
    asyncio.run(loop(pool))
