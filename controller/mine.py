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

import sim_primitives.coins as coins
import sim_primitives.mining_params as mining_params
from sim_primitives.miner import Miner
from sim_primitives.network import Connection, ConnectionFactory
from sim_primitives.pool import Pool
from sim_primitives.stratum_v2.miner import MinerV2
from sim_primitives.stratum_v2.pool import PoolV2

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

    conn1 = Connection(
        env,
        'stratum',
        mean_latency=args.latency,
        latency_stddev_percent=0 if args.no_luck else 10,
    )
    
    m1 = Miner(
        'miner1',
        env,
        bus,
        diff_1_target=mining_params.diff_1_target,
        protocol_type=MinerV2,
        device_information=dict(
            speed_ghps=10000,
            vendor='Bitmain',
            hardward_version='S9i 3.5',
            firmware='braiins-os-2018-09-22-2-hash',
            device_id='ac6f0145fccc1810',
        ),
        simulate_luck=not args.no_luck,
    )

    upstream = pool

    m1.connect_to_pool(conn1, upstream)

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
