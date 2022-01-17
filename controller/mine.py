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

import numpy as np
import simpy
from colorama import init, Fore
from event_bus import EventBus

import primitives.coins as coins
import primitives.mining_params as mining_params
from primitives.miner import Miner
from primitives.pool import Pool
from primitives.connection import Connection
import asyncio # new module 
import time

init()
bus = EventBus()

def connect():
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
        @bus.on('miner1')
        def subscribe_m1(ts, conn_uid, message):
            print(
                Fore.LIGHTRED_EX,
                'T+{0:.3f}:'.format(ts),
                '(miner1)',
                conn_uid if conn_uid is not None else '',
                message,
                Fore.RESET,
            )

    conn1 = Connection(
        env,
        'stratum',
        mean_latency=args.latency,
        latency_stddev_percent=0 if args.no_luck else 10,
        # pool_host = 'v2.stratum.slushpool.com',
        # pool_port = 3336,
        pool_host = 'localhost',
        pool_port = 2000
    )
    
    m1 = Miner(
        'miner1',
        env,
        bus,
        diff_1_target=mining_params.diff_1_target,
        device_information=dict(
            speed_ghps=10000,
            vendor='Bitmain',
            hardward_version='S9i 3.5',
            firmware='braiins-os-2018-09-22-2-hash',
            device_id='ac6f0145fccc1810',
        ),
        simulate_luck=not args.no_luck,
        connection=conn1
    )

    print("Going to connect to pool")
    m1.connect_to_pool(conn1)
    
    # mine!
    # env.run(until=args.limit)
    
    # print("Going to standard mining channel success")
    # # receive open standard mining channel success, TOOD: move to connect to pool
    # m1.receive_one()
    
    # print("Going to receive new mining job")
    # # receive new minig job
    # m1.receive_one()
    
    # print("Going to receive new prev hash")
    # # receive set new prev hash
    # m1.receive_one()

    # mine!
    # env.run(until=args.limit)

    # at this point, we need to start mining, as we have the job!
    
    return m1, conn1
    
async def listen():
    while True:
        try:
            m1.receive_one()
        except Exception as e:
            print(e)
            await asyncio.sleep(2.5)
            continue
       
async def mine():
    while True:
        if (m1.is_mining):
            m1.mine(m1.job)
        else:
            await asyncio.sleep(0.5)
            
async def main(m1: Miner):
    await asyncio.gather(
        mine(),
        listen(),
    )
        
if __name__ == '__main__':
    while True:
        (m1, conn1) = connect()
        asyncio.run(main(m1))