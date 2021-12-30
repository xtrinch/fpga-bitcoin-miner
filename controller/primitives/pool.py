"""Generic pool module"""
import hashlib

import numpy as np
import simpy
from event_bus import EventBus

import primitives.coins as coins
from primitives.hashrate_meter import HashrateMeter
from primitives.protocol import ConnectionProcessor
from primitives.connection import Connection
import socket
import base64
from dissononce.processing.handshakepatterns.interactive.NX import NXHandshakePattern
from dissononce.processing.impl.handshakestate import HandshakeState
from dissononce.processing.impl.symmetricstate import SymmetricState
from dissononce.processing.impl.cipherstate import CipherState
from dissononce.cipher.chachapoly import ChaChaPolyCipher
from dissononce.dh.x25519.x25519 import X25519DH
from dissononce.hash.blake2s import Blake2sHash
from cryptography.hazmat.primitives.asymmetric import x25519

"""Stratum V2 pool implementation

"""
import primitives.coins as coins
from primitives.protocol import ConnectionProcessor
from primitives.messages import *
from primitives.types import (
    DownstreamConnectionFlags,
    UpstreamConnectionFlags,
)
import random

class MiningJob:
    """This class allows the simulation to track per job difficulty target for
    correct accounting"""

    def __init__(self, uid: int, diff_target: coins.Target):
        """
        :param uid:
        :param diff_target: difficulty target
        """
        self.uid = uid
        self.diff_target = diff_target


class MiningJobRegistry:
    """Registry of jobs that have been assigned for mining.

    The registry intentionally doesn't remove any jobs from the simulation so that we
    can explicitly account for 'stale' hashrate. When this requirement is not needed,
    the retire_all_jobs() can be adjusted accordingly"""

    def __init__(self):
        # Tracking minimum valid job ID
        self.next_job_uid = 0
        # Registered jobs based on their uid
        self.jobs = dict()
        # Invalidated jobs just for accounting reasons
        self.invalid_jobs = dict()

    def new_mining_job(self, diff_target: coins.Target, job_id=None):
        """Prepares new mining job and registers it internally.

        :param diff_target: difficulty target of the job to be constructed
        :param job_id: optional identifier of a job. If not specified, the registry
        chooses its own identifier.
        :return new mining job or None if job with the specified ID already exists
        """
        if job_id is None:
            job_id = self.__next_job_uid()
        if job_id not in self.jobs:
            new_job = MiningJob(uid=job_id, diff_target=diff_target)
            self.jobs[new_job.uid] = new_job
        else:
            new_job = None
        return new_job

    def get_job(self, job_uid):
        """
        :param job_uid: job_uid to look for
        :return: Returns the job or None
        """
        return self.jobs.get(job_uid)

    def get_job_diff_target(self, job_uid):
        return self.jobs[job_uid].diff_target

    def get_invalid_job_diff_target(self, job_uid):
        return self.invalid_jobs[job_uid].diff_target

    def contains(self, job_uid):
        """Job ID presence check
        :return True when when such Job ID exists in the registry (it may still not
        be valid)"""
        return job_uid in self.jobs

    def contains_invalid(self, job_uid):
        """Check the invalidated job registry
        :return True when when such Job ID exists in the registry (it may still not
        be valid)"""
        return job_uid in self.invalid_jobs

    def retire_all_jobs(self):
        """Make all jobs invalid, while storing their copy for accounting reasons"""
        self.invalid_jobs.update(self.jobs)
        self.jobs = dict()

    def add_job(self, job: MiningJob):
        """
        Appends a job with an assigned ID into the registry
        :param job:
        :return:
        """
        assert (
            self.get_job(job.uid) is None
        ), 'Job {} already exists in the registry'.format(job)
        self.jobs[job.uid] = job

    def __next_job_uid(self):
        """Initializes a new job ID for this session.
        """
        curr_job_uid = self.next_job_uid
        self.next_job_uid += 1

        return curr_job_uid


class MiningSession:
    """Represents a mining session that can adjust its difficulty target"""

    min_factor = 0.25
    max_factor = 4

    def __init__(
        self,
        name: str,
        env: simpy.Environment,
        bus: EventBus,
        owner,
        diff_target: coins.Target,
        enable_vardiff,
        vardiff_time_window=None,
        vardiff_desired_submits_per_sec=None,
        on_vardiff_change=None,
    ):
        """
        """
        self.name = name
        self.env = env
        self.bus = bus
        self.owner = owner
        self.curr_diff_target = diff_target
        self.enable_vardiff = enable_vardiff
        self.meter = None
        self.vardiff_process = None
        self.vardiff_time_window_size = vardiff_time_window
        self.vardiff_desired_submits_per_sec = vardiff_desired_submits_per_sec
        self.on_vardiff_change = on_vardiff_change

        self.job_registry = MiningJobRegistry()

    @property
    def curr_target(self):
        """Derives target from current difficulty on the session"""
        return self.curr_diff_target

    def set_target(self, target):
        self.curr_diff_target = target

    def new_mining_job(self, job_uid=None):
        """Generates a new job using current session's target"""
        return self.job_registry.new_mining_job(self.curr_target, job_uid)

    def run(self):
        """Explicit activation starts any simulation processes associated with the session"""
        self.meter = HashrateMeter(self.env)
        if self.enable_vardiff:
            self.vardiff_process = self.env.process(self.__vardiff_loop())

    def account_diff_shares(self, diff: int):
        assert (
            self.meter is not None
        ), 'BUG: session not running yet, cannot account shares'
        self.meter.measure(diff)

    def terminate(self):
        """Complete shutdown of the session"""
        self.meter.terminate()
        if self.enable_vardiff:
            self.vardiff_process.interrupt()

    def __vardiff_loop(self):
        while True:
            try:
                submits_per_sec = self.meter.get_submit_per_secs()
                if submits_per_sec is None:
                    # no accepted shares, we will halve the diff
                    factor = 0.5
                else:
                    factor = submits_per_sec / self.vardiff_desired_submits_per_sec
                if factor < self.min_factor:
                    factor = self.min_factor
                elif factor > self.max_factor:
                    factor = self.max_factor
                self.curr_diff_target.div_by_factor(factor)
                self.__emit_aux_msg_on_bus(
                    'DIFF_UPDATE(target={})'.format(self.curr_diff_target)
                ),
                self.on_vardiff_change(self)
                yield self.env.timeout(self.vardiff_time_window_size)
            except simpy.Interrupt:
                break

    def __emit_aux_msg_on_bus(self, msg):
        self.bus.emit(self.name, self.env.now, self.owner, msg)


class MiningChannel:
    def __init__(self, cfg, conn_uid, channel_id):
        """
        :param cfg: configuration is represented by the full OpenStandardMiningChannel or
        OpenStandardMiningChannelSuccess message depending on which end of the channel we are on
        :param conn_uid: backlink to the connection this channel is on
        :param channel_id: unique identifier for the channel
        """
        self.cfg = cfg
        self.conn_uid = conn_uid
        self.id = channel_id

    def set_id(self, channel_id):
        self.id = channel_id


class PoolMiningChannel(MiningChannel):
    """This mining channel contains mining session and future job.

    Currently, the channel holds only 1 future job.
    """

    def __init__(self, session, *args, **kwargs):
        """
        :param session: optional mining session process (TODO: review if this is the right place)
        """
        self.future_job = None
        self.session = session
        super().__init__(*args, **kwargs)

    def terminate(self):
        self.session.terminate()

    def set_session(self, session):
        self.session = session

    def take_future_job(self):
        """Takes future job from the channel."""
        assert (
            self.future_job is not None
        ), 'BUG: Attempt to take a future job from channel: {}'.format(self.id)
        future_job = self.future_job
        self.future_job = None
        return future_job

    def add_future_job(self, job):
        """Stores future job ready for mining should a new block be found"""
        assert (
            self.future_job is None
        ), 'BUG: Attempt to overwrite an existing future job: {}'.format(self.id)
        self.future_job = job


class ChannelRegistry:
    """Keeps track of channels on individual connection"""

    def __init__(self, conn_uid):
        self.conn_uid = conn_uid
        self.channels = []

    def append(self, channel):
        """Simplify registering new channels"""
        new_channel_id = len(self.channels)
        channel.set_id(new_channel_id)
        self.channels.append(channel)

    def get_channel(self, channel_id):
        if channel_id < len(self.channels):
            return self.channels[channel_id]
        else:
            return None


class ConnectionConfig:
    """Stratum V2 connection configuration.

    For now, it is sufficient to record the SetupConnection to have full connection configuration available.
    """

    def __init__(self, msg: SetupConnection):
        self.setup_msg = msg

    @property
    def requires_version_rolling(self):
        return (
            DownstreamConnectionFlags.REQUIRES_VERSION_ROLLING in self.setup_msg.flags
        )

class Pool(ConnectionProcessor):
    """Represents a generic mining pool.

    It handles connections and delegates work to actual protocol specific object

    The pool keeps statistics about:

    - accepted submits and shares: submit count and difficulty sum (shares) for valid
    solutions
    - stale submits and shares: submit count and difficulty sum (shares) for solutions
    that have been sent after new block is found
    - rejected submits: submit count of invalid submit attempts that don't refer any
    particular job
    """

    meter_period = 60

    def __init__(
        self,
        name: str,
        env: simpy.Environment,
        bus: EventBus,
        default_target: coins.Target,
        extranonce2_size: int = 8,
        avg_pool_block_time: float = 60,
        enable_vardiff: bool = False,
        desired_submits_per_sec: float = 0.3,
        simulate_luck: bool = True,
    ):
        """

        :type pool_v2:
        """
        self.name = name
        self.env = env
        self.bus = bus
        self.default_target = default_target
        self.extranonce2_size = extranonce2_size
        self.avg_pool_block_time = avg_pool_block_time

        # Prepare initial prevhash for the very first
        self.__generate_new_prev_hash()
        # Per connection message processors
        self.connection_processors = dict()

        self.pow_update_process = env.process(self.__pow_update())

        self.meter_accepted = HashrateMeter(self.env)
        self.meter_rejected_stale = HashrateMeter(self.env)
        self.meter_process = env.process(self.__pool_speed_meter())
        self.enable_vardiff = enable_vardiff
        self.desired_submits_per_sec = desired_submits_per_sec
        self.simulate_luck = simulate_luck

        self.extra_meters = []

        self.accepted_submits = 0
        self.stale_submits = 0
        self.rejected_submits = 0

        self.accepted_shares = 0
        self.stale_shares = 0

    def make_handshake(self, connection: Connection): 
        self.connection = connection
              
        connection.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        connection.sock.bind(('localhost', 2000))
        connection.sock.listen(1)
        print("Listening for connections")

        connection.conn_target, addr = connection.sock.accept()
        print('Accepted connection from', addr)

        # our_private = base64.b64decode('WAmgVYXkbT2bCtdcDwolI88/iVi/aV3/PHcUBTQSYmo=')
        # private = x25519.X25519PrivateKey.from_private_bytes(our_private)

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
        ciphertext = connection.conn_target.recv(4096)
        frame, _ = Connection.unwrap(ciphertext)
        message_buffer = bytearray()
        our_handshakestate.read_message(frame, message_buffer)

        # when we do, respond
        ## in the buffer, there should be Signature Noise Message, but we 
        ## obviously don't really know how to construct it, so we'll skip it for localhost
        message_buffer = bytearray()
        self.connection.cipherstates = our_handshakestate.write_message(b"", message_buffer)
        self.connection.cipher_state = self.connection.cipherstates[1]
        self.connection.decrypt_cipher_state = self.connection.cipherstates[0]

        message_buffer = Connection.wrap(bytes(message_buffer))
        num_sent = connection.conn_target.send(message_buffer)  # rpc send
        
    def reset_stats(self):
        self.accepted_submits = 0
        self.stale_submits = 0
        self.rejected_submits = 0
        self.accepted_shares = 0
        self.stale_shares = 0

    def disconnect(self, connection: Connection):
        if connection.uid not in self.connection_processors:
            return
        self.connection_processors[connection.uid].terminate()
        del self.connection_processors[connection.uid]

    def new_mining_session(self, owner, on_vardiff_change, clz=MiningSession):
        """Creates a new mining session"""
        session = clz(
            name=self.name,
            env=self.env,
            bus=self.bus,
            owner=owner,
            diff_target=self.default_target,
            enable_vardiff=self.enable_vardiff,
            vardiff_time_window=self.meter_accepted.window_size,
            vardiff_desired_submits_per_sec=self.desired_submits_per_sec,
            on_vardiff_change=on_vardiff_change,
        )
        self.__emit_aux_msg_on_bus('NEW MINING SESSION ()'.format(session))

        return session

    def add_extra_meter(self, meter: HashrateMeter):
        self.extra_meters.append(meter)

    def account_accepted_shares(self, diff_target: coins.Target):
        self.accepted_submits += 1
        self.accepted_shares += diff_target.to_difficulty()
        self.meter_accepted.measure(diff_target.to_difficulty())

    def account_stale_shares(self, diff_target: coins.Target):
        self.stale_submits += 1
        self.stale_shares += diff_target.to_difficulty()
        self.meter_rejected_stale.measure(diff_target.to_difficulty())

    def account_rejected_submits(self):
        self.rejected_submits += 1

    def process_submit(
        self, submit_job_uid, session: MiningSession, on_accept, on_reject
    ):
        if session.job_registry.contains(submit_job_uid):
            diff_target = session.job_registry.get_job_diff_target(submit_job_uid)
            # Global accounting
            self.account_accepted_shares(diff_target)
            # Per session accounting
            session.account_diff_shares(diff_target.to_difficulty())
            on_accept(diff_target)
        elif session.job_registry.contains_invalid(submit_job_uid):
            diff_target = session.job_registry.get_invalid_job_diff_target(
                submit_job_uid
            )
            self.account_stale_shares(diff_target)
            on_reject(diff_target)
        else:
            self.account_rejected_submits()
            on_reject(None)

    def __pow_update(self):
        """This process simulates finding new blocks based on pool's hashrate"""
        while True:
            # simulate pool block time using exponential distribution
            yield self.env.timeout(
                np.random.exponential(self.avg_pool_block_time)
                if self.simulate_luck
                else self.avg_pool_block_time
            )
            # Simulate the new block hash by calculating sha256 of current time
            self.__generate_new_prev_hash()

            self.__emit_aux_msg_on_bus('NEW_BLOCK: {}'.format(self.prev_hash.hex()))

            for connection_processor in self.connection_processors.values():
                connection_processor.on_new_block()
                
    def __generate_new_prev_hash(self):
        """Generates a new prevhash based on current time.
        """
        # TODO: this is not very precise as to events that would trigger this method in
        #  the same second would yield the same prev hash value,  we should consider
        #  specifying prev hash as a simple sequence number
        self.prev_hash = hashlib.sha256(bytes(int(self.env.now))).digest()

    def __pool_speed_meter(self):
        while True:
            yield self.env.timeout(self.meter_period)
            speed = self.meter_accepted.get_speed()
            submit_speed = self.meter_accepted.get_submit_per_secs()
            if speed is None or submit_speed is None:
                self.__emit_aux_msg_on_bus('SPEED: N/A Gh/s, N/A submits/s')
            else:
                self.__emit_aux_msg_on_bus(
                    'SPEED: {0:.2f} Gh/s, {1:.4f} submits/s'.format(speed, submit_speed)
                )

    def __emit_aux_msg_on_bus(self, msg):
        self.bus.emit(self.name, self.env.now, None, msg)

    def run(self):
        print("GOING TO RUN POOL")
        pass

    def _send_msg(self, msg):
        self.connection.send_msg(msg)

    def _recv_msg(self):
        return self.connection.outgoing.get()
    
    def terminate(self):
        super().terminate()
        for channel in self._mining_channel_registry.channels:
            channel.terminate()

    def _on_invalid_message(self, msg):
        """Ignore any unrecognized messages.

        TODO-DOC: define protocol handling of unrecognized messages
        """
        pass

    def visit_setup_connection(self, msg: SetupConnection):
        # response_flags = set()

        # arbitrary for now
        # if DownstreamConnectionFlags.REQUIRES_VERSION_ROLLING not in msg.flags:
        # response_flags.add(UpstreamConnectionFlags.REQUIRES_FIXED_VERSION)
        print("sending connection success")
        self._send_msg(
            SetupConnectionSuccess(
                used_version=min(msg.min_version, msg.max_version),
                flags=0,
            )
        )

    def visit_open_standard_mining_channel(self, msg: OpenStandardMiningChannel):
        # Open only channels compatible with this node's configuration
        if msg.max_target <= self.default_target.diff_1_target:
            # Create the channel and build back-links from session to channel and from
            # channel to connection
            mining_channel = PoolMiningChannel(
                cfg=msg, conn_uid=self.connection.uid, channel_id=None, session=None
            )
            # Appending assigns the channel a unique ID within this connection
            # self._mining_channel_registry.append(mining_channel)

            # TODO use partial to bind the mining channel to the _on_vardiff_change and eliminate the need for the
            #  backlink
            session = self.new_mining_session(
                owner=mining_channel, on_vardiff_change=self._on_vardiff_change
            )
            mining_channel.set_session(session)
            mining_channel.id = random.randint(0, 16777216)

            self._send_msg(
                OpenStandardMiningChannelSuccess(
                    req_id=msg.req_id,
                    channel_id=mining_channel.id,
                    target=session.curr_target.target,
                    extranonce_prefix=b'',
                    group_channel_id=0,  # pool currently doesn't support grouping
                )
            )

            # TODO-DOC: explain the (mandatory?) setting 'future_job=True' in
            #  the message since the downstream has no prev hash
            #  immediately after the OpenStandardMiningChannelSuccess
            #  Update the flow diagram in the spec including specifying the
            #  future_job attribute
            new_job_msg = self.__build_new_job_msg(mining_channel, is_future_job=True)
            # Take the future job from the channel so that we have space for producing a new one right away
            future_job = mining_channel.take_future_job()
            assert (
                future_job.uid == new_job_msg.job_id
            ), "BUG: future job on channel {} doesn't match the produced message job ID {}".format(
                future_job.uid, new_job_msg.job_id
            )
            self._send_msg(new_job_msg)
            self._send_msg(
                self.__build_set_new_prev_hash_msg(
                    channel_id=mining_channel.id, future_job_id=new_job_msg.job_id
                )
            )
            # Send out another future job right away
            future_job_msg = self.__build_new_job_msg(
                mining_channel, is_future_job=True
            )
            self._send_msg(future_job_msg)

            # All messages sent, start the session
            session.run()

        else:
            self._send_msg(
                OpenMiningChannelError(
                    msg.req_id, 'Cannot open mining channel: {}'.format(msg)
                )
            )

    def visit_submit_shares_standard(self, msg: SubmitSharesStandard):
        """
        TODO: implement aggregation of sending SubmitSharesSuccess for a batch of successful submits
        """
        channel = self._mining_channel_registry.get_channel(msg.channel_id)

        assert (
            channel.conn_uid == self.connection.uid
        ), "Channel conn UID({}) doesn't match current conn UID({})".format(
            channel.conn_uid, self.connection.uid
        )
        self.__emit_channel_msg_on_bus(msg)

        def on_accept(diff_target: coins.Target):
            resp_msg = SubmitSharesSuccess(
                channel.id,
                last_sequence_number=msg.sequence_number,
                new_submits_accepted_count=1,
                new_shares_sum=diff_target.to_difficulty(),
            )
            self._send_msg(resp_msg)
            self.__emit_channel_msg_on_bus(resp_msg)

        def on_reject(_diff_target: coins.Target):
            resp_msg = SubmitSharesError(
                channel.id,
                sequence_number=msg.sequence_number,
                error_code='Share rejected',
            )
            self._send_msg(resp_msg)
            self.__emit_channel_msg_on_bus(resp_msg)

        self.process_submit(
            msg.job_id, channel.session, on_accept=on_accept, on_reject=on_reject
        )

    def visit_submit_shares_extended(self, msg: SubmitSharesStandard):
        pass

    def _on_vardiff_change(self, session: MiningSession):
        """Handle difficulty change for the current session.

        Note that to enforce difficulty change as soon as possible,
        the message is accompanied by generating new mining job
        """
        channel = session.owner
        self._send_msg(SetTarget(channel.id, session.curr_target))

        new_job_msg = self.__build_new_job_msg(channel, is_future_job=False)
        self._send_msg(new_job_msg)

    def on_new_block(self):
        """Sends an individual SetNewPrevHash message to all channels

        TODO: it is not quite clear how to handle the case where downstream has
         open multiple channels with the pool. The following needs to be
         answered:
         - Is any downstream node that opens more than 1 mining channel considered a
           proxy = it understands  grouping? MAYBE/YES but see next questions
         - Can we send only 1 SetNewPrevHash message even if the channels are
           standard? NO - see below
         - if only 1 group SetNewPrevHash message is sent what 'future' job should
           it reference? The problem is that we have no defined way where a future
           job is being shared by multiple channels.
        """
        # Pool currently doesn't support grouping channels, all channels belong to
        # group 0. We set the prev hash for all channels at once
        # Retire current jobs in the registries of all channels
        for channel in self._mining_channel_registry.channels:
            future_job = channel.take_future_job()
            prev_hash_msg = self.__build_set_new_prev_hash_msg(
                channel.id, future_job.uid
            )
            channel.session.job_registry.retire_all_jobs()
            channel.session.job_registry.add_job(future_job)
            # Now, we can send out the new prev hash, since all jobs are
            # invalidated. Any further submits for the invalidated jobs will be
            # rejected
            self._send_msg(prev_hash_msg)

        # We can now broadcast future jobs to all channels for the upcoming block
        for channel in self._mining_channel_registry.channels:
            future_new_job_msg = self.__build_new_job_msg(channel, is_future_job=True)
            self._send_msg(future_new_job_msg)

    def __build_set_new_prev_hash_msg(self, channel_id, future_job_id):
        return SetNewPrevHash(
            channel_id=channel_id,
            job_id=future_job_id,
            prev_hash=self.prev_hash,
            min_ntime=self.env.now,
            nbits=None,
        )

    @staticmethod
    def __build_new_job_msg(mining_channel: PoolMiningChannel, is_future_job: bool):
        """Builds NewMiningJob or NewExtendedMiningJob depending on channel type.

        The method also builds the actual job and registers it as 'future' job within
        the channel if requested.

        :param channel: determines the channel and thus message type
        :param is_future_job: when true, the job won't be considered for the current prev
         hash known to the downstream node but for any future prev hash that explicitly
         selects it
        :return New{Extended}MiningJob
        """
        new_job = mining_channel.session.new_mining_job()
        if is_future_job:
            mining_channel.add_future_job(new_job)

        # Compose the protocol message based on actual channel type
        if isinstance(mining_channel.cfg, OpenStandardMiningChannel):
            msg = NewMiningJob(
                channel_id=mining_channel.id,
                job_id=new_job.uid,
                future_job=is_future_job,
                version=1,
                merkle_root=1, # Hash() ?
            )
        elif isinstance(mining_channel.cfg, OpenExtendedMiningChannel):
            msg = NewExtendedMiningJob(
                channel_id=mining_channel.id,
                job_id=new_job.uid,
                future_job=is_future_job,
                version=1,
                version_rolling_allowed=True,  # TODO
                merkle_path=MerklePath(),
                cb_prefix=CoinBasePrefix(),
                cb_suffix=CoinBaseSuffix(),
            )
        else:
            assert False, 'Unsupported channel type: {}'.format(
                mining_channel.cfg.channel_type
            )

        return msg

    def __emit_channel_msg_on_bus(self, msg: ChannelMessage):
        """Helper method for reporting a channel oriented message on the debugging bus."""
        self._emit_protocol_msg_on_bus('Channel ID: {}'.format(msg.channel_id), msg)
