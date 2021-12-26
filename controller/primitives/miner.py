import numpy as np
import simpy
from event_bus import EventBus

import primitives.coins as coins
from primitives.hashrate_meter import HashrateMeter
from primitives.connection import Connection
from primitives.pool import MiningSession, MiningJob, Pool
from primitives.protocol import ConnectionProcessor

import enum

import primitives.coins as coins
from primitives.connection import Connection
from primitives.pool import MiningJob
from primitives.messages import (
    SetupConnection,
    SetupConnectionSuccess,
    SetupConnectionError,
    OpenStandardMiningChannel,
    OpenStandardMiningChannelSuccess,
    OpenMiningChannelError,
    SetNewPrevHash,
    SetTarget,
    NewMiningJob,
    SubmitSharesStandard,
    SubmitSharesSuccess,
    SubmitSharesError,
)
from primitives.pool import PoolMiningChannel
from primitives.types import ProtocolType, DownstreamConnectionFlags


class Miner(object):
    def __init__(
        self,
        name: str,
        env: simpy.Environment,
        bus: EventBus,
        diff_1_target: int,
        device_information: dict,
        simulate_luck=True,
        *args,
        **kwargs
    ):
        self.name = name
        self.env = env
        self.bus = bus
        self.diff_1_target = diff_1_target
        self.device_information = device_information
        self.miner = None
        self.work_meter = HashrateMeter(env)
        self.mine_proc = None
        self.job_uid = None
        self.share_diff = None
        self.recv_loop_process = None
        self.is_mining = True
        self.simulate_luck = simulate_luck

    def get_actual_speed(self):
        return self.device_information.get('speed_ghps') if self.is_mining else 0

    def mine(self, job: MiningJob):        
        share_diff = job.diff_target.to_difficulty()
        avg_time = share_diff * 4.294967296 / self.device_information.get('speed_ghps')

        # Report the current hashrate at the beginning when of mining
        self.__emit_hashrate_msg_on_bus(job, avg_time)

        while True:
            try:
                yield self.env.timeout(
                    np.random.exponential(avg_time) if self.simulate_luck else avg_time
                )
            except simpy.Interrupt:
                self.__emit_aux_msg_on_bus('Mining aborted (external signal)')
                break

            # To simulate miner failures we can disable mining
            if self.is_mining:
                self.work_meter.measure(share_diff)
                self.__emit_hashrate_msg_on_bus(job, avg_time)
                self.__emit_aux_msg_on_bus('solution found for job {}'.format(job.uid))

                self.miner.submit_mining_solution(job)

    def connect_to_pool(self, connection: Connection):
        assert self.miner is None, 'BUG: miner is already connected'
        
        connection.connect_to()

        # Intializes MinerV2 instance
        self.miner = MinerV2(self, connection)
        self.miner.setup_connection()
        
        self.__emit_aux_msg_on_bus('Connecting to pool {}:{}'.format(connection.pool_host, connection.pool_port))

    def disconnect(self):
        self.__emit_aux_msg_on_bus('Disconnecting from pool')
        if self.mine_proc:
            self.mine_proc.interrupt()
        # Mining is shutdown, terminate any protocol message processing
        self.miner.terminate()
        self.miner.disconnect()
        self.miner = None

    def new_mining_session(self, diff_target: coins.Target):
        """Creates a new mining session"""
        session = MiningSession(
            name=self.name,
            env=self.env,
            bus=self.bus,
            # TODO remove once the backlinks are not needed
            owner=None,
            diff_target=diff_target,
            enable_vardiff=False,
        )
        self.__emit_aux_msg_on_bus('NEW MINING SESSION ()'.format(session))
        return session

    def mine_on_new_job(self, job: MiningJob, flush_any_pending_work=True):
        """Start working on a new job

         TODO implement more advanced flush policy handling (e.g. wait for the current
          job to finish if flush_flush_any_pending_work is not required)
        """
        # Interrupt the mining process for now
        if self.mine_proc is not None:
            self.mine_proc.interrupt()
        # Restart the process with a new job
        self.mine_proc = self.env.process(self.mine(job))

    def set_is_mining(self, is_mining):
        self.is_mining = is_mining

    def __emit_aux_msg_on_bus(self, msg: str):
        self.bus.emit(
            self.name,
            self.env.now,
            self.miner.connection.uid
            if self.miner
            else None,
            msg,
        )

    def __emit_hashrate_msg_on_bus(self, job: MiningJob, avg_share_time):
        """Reports hashrate statistics on the message bus

        :param job: current job that is being mined
        :return:
        """
        self.__emit_aux_msg_on_bus(
            'mining with diff {} | speed {} Gh/s | avg share time {} | job uid {}'.format(
                job.diff_target.to_difficulty(),
                self.work_meter.get_speed(),
                avg_share_time,
                job.uid,
            )
        )

# TODO: Move MiningChannel and session from Pool
class MinerV2(ConnectionProcessor):
    class States(enum.Enum):
        INIT = 0
        CONNECTION_SETUP = 1

    def __init__(self, miner: Miner, connection: Connection):
        self.miner = miner
        self.state = self.States.INIT
        self.channel = None
        super().__init__(miner.name, miner.env, miner.bus, connection)
        self.connection_config = None

    def setup_connection(self):
        # Initiate V2 protocol setup
        # TODO-DOC: specification should categorize downstream and upstream flags.
        #  PubKey handling is also not precisely defined yet
        print("Send Setup Connection MSG")
        self.connection.send_msg(
            SetupConnection(
                protocol=ProtocolType.MINING_PROTOCOL,
                max_version=2,
                min_version=2,
                flags=0,  # TODO:
                endpoint_host=self.connection.pool_host,
                endpoint_port=self.connection.pool_port,
                vendor=self.miner.device_information.get('vendor', 'unknown'),
                hardware_version=self.miner.device_information.get(
                    'hardware_version', 'unknown'
                ),
                firmware=self.miner.device_information.get('firmware', 'unknown'),
                device_id=self.miner.device_information.get('device_id', ''),
            )
        )
        print("Going to receive setup connection success")
        # we are expecting setup connection success;
        # upon receiving success we send back OpenStandardMiningChannel via the
        # visit_setup_connection_success
        self.receive_one()
        
    class ConnectionConfig:
        """Stratum V2 connection configuration.

        For now, it is sufficient to record the SetupConnectionSuccess to have full
        connection configuration available.
        """

        def __init__(self, msg: SetupConnectionSuccess):
            self.setup_msg = msg
            
    def _recv_msg(self):
        return self.connection.incoming.get()

    def disconnect(self):
        """Downstream node may initiate disconnect

        """
        self.connection.disconnect()

    def _on_invalid_message(self, msg):
        pass

    def visit_setup_connection_success(self, msg: SetupConnectionSuccess):
        print("Visit setup connection sucess")
        self._emit_protocol_msg_on_bus('Connection setup', msg)
        self.connection_config = self.ConnectionConfig(msg)
        self.state = self.States.CONNECTION_SETUP

        print("Sending open standard mining channel")
        req = OpenStandardMiningChannel(
            req_id=1,
            user_identity=self.name,
            nominal_hashrate=self.miner.device_information.get('speed_ghps') * 1e9,
            max_target=self.miner.diff_1_target,
            # Header only mining, now extranonce 2 size required
        )
        # We expect a paired response to our open channel request
        self.send_request(req)

    def visit_setup_connection_error(self, msg: SetupConnectionError):
        """Setup connection has failed.

        TODO: consider implementing reconnection attempt with exponential backoff or
         something similar
        """
        self._emit_protocol_msg_on_bus('Connection setup failed', msg)

    def visit_open_standard_mining_channel_success(
        self, msg: OpenStandardMiningChannelSuccess
    ):
        req = self.request_registry.pop(msg.req_id)

        if req is not None:
            session = self.miner.new_mining_session(
                coins.Target(msg.target, self.miner.diff_1_target)
            )
            # TODO find some reasonable extraction of the channel configuration, for now,
            #  we just retain the OpenMiningChannel and OpenMiningChannelSuccess message
            #  pair that provides complete information
            self.channel = PoolMiningChannel(
                session=session,
                cfg=(req, msg),
                conn_uid=self.connection.uid,
                channel_id=msg.channel_id,
            )
            session.run()
        else:
            self._emit_protocol_msg_on_bus(
                'Cannot find matching OpenMiningChannel request', msg
            )

    def visit_open_extended_mining_channel_success(
        self, msg: OpenStandardMiningChannelSuccess
    ):
        pass

    def visit_open_mining_channel_error(self, msg: OpenMiningChannelError):
        req = self.request_registry.pop(msg.req_id)
        self._emit_protocol_msg_on_bus(
            'Open mining channel failed (orig request: {})'.format(req), msg
        )

    def visit_set_target(self, msg: SetTarget):
        if self.__is_channel_valid(msg):
            self.channel.session.set_target(msg.max_target)

    def visit_set_new_prev_hash(self, msg: SetNewPrevHash):
        if self.__is_channel_valid(msg):
            if self.channel.session.job_registry.contains(msg.job_id):
                self.miner.mine_on_new_job(
                    job=self.channel.session.job_registry.get_job(msg.job_id),
                    flush_any_pending_work=True,
                )

    def visit_new_mining_job(self, msg: NewMiningJob):
        if self.__is_channel_valid(msg):
            # Prepare a new job with the current session difficulty target
            job = self.channel.session.new_mining_job(job_uid=msg.job_id)
            # Schedule the job for mining
            if not msg.future_job:
                self.miner.mine_on_new_job(job)

    def visit_submit_shares_success(self, msg: SubmitSharesSuccess):
        if self.__is_channel_valid(msg):
            self.channel.session.account_diff_shares(msg.new_shares_sum)

    def visit_submit_shares_error(self, msg: SubmitSharesError):
        if self.__is_channel_valid(msg):
            # TODO implement accounting for rejected shares
            pass
            # self.channel.session.account_rejected_shares(msg.new_shares_sum)

    def submit_mining_solution(self, job: MiningJob):
        """Callback from the physical miner that succesfully simulated mining some shares

        :param job: Job that the miner has been working on and found solution for it
        """
        # TODO: seq_num is currently unused, we should use it for tracking
        #  accepted/rejected shares
        self.connection._send_msg(
            SubmitSharesStandard(
                channel_id=self.channel.id,
                sequence_number=0,  # unique sequential identifier within the channel.
                job_id=job.uid,
                nonce=0,
                ntime=self.env.now,
                version=0,  # full nVersion field
            )
        )

    def _on_invalid_message(self, msg):
        self._emit_protocol_msg_on_bus('Received invalid message', msg)

    def __is_channel_valid(self, msg):
        """Validates channel referenced in the message is the open channel of the miner"""
        if self.channel is None:
            bus_error_msg = (
                'Mining Channel not established yet, received channel '
                'message with channel ID({})'.format(msg.channel_id)
            )
            is_valid = False
            self._emit_protocol_msg_on_bus(bus_error_msg, msg)
        elif self.channel.id != msg.channel_id:
            bus_error_msg = 'Unknown channel (expected: {}, actual: {})'.format(
                self.channel.channel_id, msg.channel_id
            )
            is_valid = False
            self._emit_protocol_msg_on_bus(bus_error_msg, msg)
        else:
            is_valid = True

        return is_valid

    def run(self):
        pass