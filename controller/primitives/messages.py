# see https://github.com/stratumv2/stratumv2/blob/master/messages.py it has some parsing already

import typing

import stringcase

from .protocol_types import *

"""Stratum V2 messages."""
from primitives.types import CoinBasePrefix, CoinBaseSuffix, Hash, MerklePath


class Message:
    """Generic message that accepts visitors and dispatches their processing."""

    class VisitorMethodNotImplemented(Exception):
        """Custom handling to report if visitor method is missing"""

        def __init__(self, method_name):
            self.method_name = method_name

        def __str__(self):
            return self.method_name

    def __init__(self, req_id=None):
        self.req_id = req_id

    def accept(self, visitor):
        """Call visitor method based on the actual message type."""
        method_name = "visit_{}".format(stringcase.snakecase(type(self).__name__))

        print(method_name)

        try:
            visit_method = getattr(visitor, method_name)
        except AttributeError:
            raise self.VisitorMethodNotImplemented(method_name)

        visit_method(self)

    def _format(self, content):
        return "{}({})".format(type(self).__name__, content)


class ChannelMessage(Message):
    """Message specific for a channel identified by its channel_id"""

    def __init__(self, channel_id: int, *args, **kwargs):
        self.channel_id = channel_id
        super().__init__(*args, **kwargs)


class SetupConnection(Message):
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
        device_id: str = "",
    ):
        self.protocol = protocol
        self.max_version = max_version
        self.min_version = min_version
        self.flags = flags
        self.endpoint_host = endpoint_host
        self.endpoint_port = endpoint_port
        # Device information
        self.vendor = vendor
        self.hardware_version = hardware_version
        self.firmware = firmware
        self.device_id = device_id
        super().__init__()

    def __str__(self):
        return self._format(
            "protocol={}, max_version={}, min_version={}, flags={}, endpoint_host={}, endpoint_port={}, vendor={}, hardware_version={}, firmware={}, device_id={}".format(
                self.protocol,
                self.max_version,
                self.min_version,
                self.flags,
                self.endpoint_host,
                self.endpoint_port,
                self.vendor,
                self.hardware_version,
                self.firmware,
                self.device_id,
            )
        )

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

        payload = (
            protocol
            + min_version
            + max_version
            + flags
            + endpoint_host
            + endpoint_port
            + vendor
            + hardware_version
            + firmware
            + device_id
        )
        frame = FRAME(0x0, "SetupConnection", payload)

        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        length_offset = 0

        protocol = bytes[0]  # 1 byte
        min_version = int.from_bytes(bytes[1:3], byteorder="little")  # 2 bytes
        max_version = int.from_bytes(bytes[3:5], byteorder="little")  # 2 bytes
        flags = int.from_bytes(bytes[5:9], byteorder="little")  # 4 bytes

        endpoint_length = bytes[9]
        endpoint_host = bytes[10 : 10 + endpoint_length].decode("utf-8")
        endpoint_port = int.from_bytes(
            bytes[10 + endpoint_length : 12 + endpoint_length], byteorder="little"
        )
        length_offset += endpoint_length

        vendor_length = bytes[12 + length_offset]
        vendor = bytes[13 + length_offset : 13 + length_offset + vendor_length].decode(
            "utf-8"
        )
        length_offset += vendor_length

        hardware_version_length = bytes[13 + length_offset]
        hardware_version = bytes[
            14 + length_offset : 14 + length_offset + hardware_version_length
        ].decode("utf-8")
        length_offset += hardware_version_length

        firmware_length = bytes[14 + length_offset]
        firmware = bytes[
            15 + length_offset : 15 + length_offset + firmware_length
        ].decode("utf-8")
        length_offset += firmware_length

        device_id_length = bytes[15 + length_offset]
        device_id = bytes[
            16 + length_offset : 16 + length_offset + device_id_length
        ].decode("utf-8")

        msg = SetupConnection(
            protocol=protocol,
            min_version=min_version,
            max_version=max_version,
            flags=flags,
            endpoint_host=endpoint_host,
            endpoint_port=endpoint_port,
            vendor=vendor,
            hardware_version=hardware_version,
            firmware=firmware,
            device_id=device_id,
        )
        return msg


class SetupConnectionSuccess(Message):
    def __init__(self, used_version: int, flags: int):
        self.used_version = used_version
        self.flags = flags
        super().__init__()

    def __str__(self):
        return self._format(
            "used_version={}, flags={}".format(
                self.used_version,
                self.flags,
            )
        )

    def to_bytes(self):
        used_version = U16(self.used_version)
        flags = U32(self.flags)
        payload = used_version + flags

        frame = FRAME(0x0, "SetupConnectionSuccess", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        used_version = int.from_bytes(bytes[0:2], byteorder="little")  # 2 bytes
        flags = int.from_bytes(bytes[2:6], byteorder="little")  # bytes

        msg = SetupConnectionSuccess(
            used_version=used_version,
            flags=flags,
        )
        return msg


class SetupConnectionError(Message):
    def __init__(self, flags: list, error_code: str):
        self.flags = flags
        self.error_code = error_code
        super().__init__()


# Mining Protocol Messages
class OpenStandardMiningChannel(Message):
    def __init__(
        self,
        req_id: typing.Any,
        user_identity: str,
        nominal_hashrate: float,
        max_target: int,
    ):
        """ """
        self.user_identity = user_identity
        self.nominal_hashrate = nominal_hashrate
        self.max_target = max_target
        self.new_job_class = NewMiningJob
        super().__init__(req_id)

    def __str__(self):
        return self._format(
            "req_id={}, user_identity={}, nominal_hashrate={}, max_target={}, new_job_class={}".format(
                self.req_id,
                self.user_identity,
                self.nominal_hashrate,
                self.max_target,
                self.new_job_class,
            )
        )

    def to_bytes(self):
        req_id = U32(self.req_id)
        user_identity = STR0_255(self.user_identity)
        nominal_hashrate = F32(self.nominal_hashrate)
        max_target = U256(self.max_target)

        payload = req_id + user_identity + nominal_hashrate + max_target

        frame = FRAME(0x0, "OpenStandardMiningChannel", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        req_id = int.from_bytes(bytes[0:4], byteorder="little")

        l = bytes[4]

        user_identity = bytes[5 : 5 + l].decode("utf-8")
        nominal_hashrate = struct.unpack("<f", bytes[5 + l : 5 + l + 4])
        max_target = int.from_bytes(
            bytes[5 + l + 4 : 5 + l + 4 + 4], byteorder="little"
        )

        msg = OpenStandardMiningChannel(
            req_id=req_id,
            user_identity=user_identity,
            nominal_hashrate=nominal_hashrate,
            max_target=max_target,
        )
        return msg


class OpenStandardMiningChannelSuccess(ChannelMessage):
    def __init__(
        self,
        req_id: typing.Any,
        channel_id: int,
        target: int,
        extranonce_prefix: bytes,
        group_channel_id: int,
    ):
        self.req_id = req_id
        self.target = target
        self.channel_id = channel_id
        self.group_channel_id = group_channel_id
        self.extranonce_prefix = extranonce_prefix
        super().__init__(channel_id=channel_id, req_id=req_id)

    def __str__(self):
        return self._format(
            "req_id={}, channel_id={}, target={}, extranonce_prefix={}, group_channel_id={}".format(
                self.req_id,
                self.channel_id,
                self.target,
                self.extranonce_prefix,
                self.group_channel_id,
            )
        )

    @staticmethod
    def from_bytes(bytes: bytearray):
        req_id = int.from_bytes(bytes[0:4], byteorder="little")
        channel_id = int.from_bytes(bytes[4:8], byteorder="little")  # this is correct!!
        target = int.from_bytes(bytes[9 : 9 + 31], byteorder="little")

        l = bytes[9 + 31]

        extranonce_prefix = int.from_bytes(bytes[41 : 41 + l], byteorder="little")
        group_channel_id = int.from_bytes(bytes[41 + l : 46 + l], byteorder="little")

        msg = OpenStandardMiningChannelSuccess(
            req_id=req_id,
            channel_id=channel_id,
            target=target,
            extranonce_prefix=extranonce_prefix,
            group_channel_id=group_channel_id,
        )
        return msg

    def to_bytes(self):
        req_id = U32(self.req_id)
        channel_id = U32(self.channel_id)
        target = U256(self.target)
        extranonce_prefix = B0_32(self.extranonce_prefix)
        group_channel_id = U32(self.group_channel_id)

        payload = req_id + channel_id + target + extranonce_prefix + group_channel_id

        frame = FRAME(0x0, "OpenStandardMiningChannelSuccess", payload)
        return frame

    def msg_type_name(self):
        return "OpenStandardMiningChannelSuccess"


class OpenExtendedMiningChannel(OpenStandardMiningChannel):
    def __init__(self, min_extranonce_size: int, *args, **kwargs):
        self.min_extranonce_size = min_extranonce_size
        self.new_job_class = NewExtendedMiningJob
        super().__init__(*args, **kwargs)


class OpenExtendedMiningChannelSuccess(ChannelMessage):
    def __init__(
        self,
        req_id,
        channel_id: int,
        target: int,
        extranonce_size: int,
        extranonce_prefix: bytes,
    ):
        self.target = target
        self.extranonce_prefix = extranonce_prefix
        self.extranonce_size = extranonce_size
        super().__init__(channel_id=channel_id, req_id=req_id)


class OpenMiningChannelError(Message):
    def __init__(self, req_id, error_code: str):
        self.req_id = req_id
        self.error_code = error_code
        super().__init__(req_id)


class UpdateChannel(ChannelMessage):
    def __init__(self, channel_id: int, nominal_hash_rate: float, maximum_target: int):
        self.nominal_hash_rate = nominal_hash_rate
        self.maximum_target = maximum_target
        super().__init__(channel_id=channel_id)


class UpdateChannelError(ChannelMessage):
    def __init__(self, channel_id: int, error_code: str):
        self.error_code = error_code
        super().__init__(channel_id=channel_id)


class CloseChannel(ChannelMessage):
    def __init__(self, channel_id: int, reason_code: str):
        self.reason_code = reason_code
        super().__init__(channel_id=channel_id)


class SetExtranoncePrefix(ChannelMessage):
    def __init__(self, channel_id: int, extranonce_prefix: bytes):
        self.extranonce_prefix = extranonce_prefix
        super().__init__(channel_id=channel_id)


class SubmitSharesStandard(ChannelMessage):
    def __init__(
        self,
        channel_id: int,
        sequence_number: int,
        job_id: int,
        nonce: int,
        ntime: int,
        version: int,
    ):
        self.sequence_number = sequence_number
        self.job_id = job_id
        self.nonce = nonce
        self.ntime = ntime
        self.version = version
        super().__init__(channel_id)

    def __str__(self):
        return self._format(
            "channel_id={}, job_id={}".format(self.channel_id, self.job_id)
        )

    def to_bytes(self):
        channel_id = U32(self.channel_id)
        sequence_number = U32(self.sequence_number)
        job_id = U32(self.job_id)
        nonce = U32(self.nonce)
        ntime = U32(self.ntime)
        version = U32(self.version)

        payload = channel_id + sequence_number + job_id + nonce + ntime + version

        frame = FRAME(0x0, "SubmitSharesStandard", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        channel_id = int.from_bytes(bytes[0:4], byteorder="little")
        sequence_number = int.from_bytes(bytes[4:8], byteorder="little")
        job_id = int.from_bytes(bytes[8:12], byteorder="little")
        nonce = int.from_bytes(bytes[12:16], byteorder="little")
        ntime = int.from_bytes(bytes[16:20], byteorder="little")
        version = int.from_bytes(bytes[20:24], byteorder="little")

        msg = SubmitSharesStandard(
            channel_id=channel_id,
            sequence_number=sequence_number,
            job_id=job_id,
            nonce=nonce,
            ntime=ntime,
            version=version,
        )
        return msg


class SubmitSharesExtended(SubmitSharesStandard):
    def __init__(self, extranonce, *args, **kwargs):
        self.extranonce = extranonce
        super().__init__(*args, **kwargs)


class SubmitSharesSuccess(ChannelMessage):
    def __init__(
        self,
        channel_id: int,
        last_sequence_number: int,
        new_submits_accepted_count: int,
        new_shares_sum: int,
    ):
        self.last_sequence_number = last_sequence_number
        self.new_submits_accepted_count = new_submits_accepted_count
        self.new_shares_sum = new_shares_sum
        super().__init__(channel_id)

    def __str__(self):
        return self._format(
            "channel_id={}, last_seq_num={}, accepted_submits={}, accepted_shares={}".format(
                self.channel_id,
                self.last_sequence_number,
                self.new_submits_accepted_count,
                self.new_shares_sum,
            )
        )

    def to_bytes(self):
        channel_id = U32(self.channel_id)
        last_sequence_number = U32(self.last_sequence_number)
        new_submits_accepted_count = U32(self.new_submits_accepted_count)
        new_shares_sum = U32(self.new_shares_sum)

        payload = (
            channel_id
            + last_sequence_number
            + new_submits_accepted_count
            + new_shares_sum
        )

        frame = FRAME(0x0, "SubmitSharesSuccess", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        channel_id = int.from_bytes(bytes[0:4], byteorder="little")
        last_sequence_number = int.from_bytes(bytes[4:8], byteorder="little")
        new_submits_accepted_count = int.from_bytes(bytes[8:12], byteorder="little")
        new_shares_sum = int.from_bytes(bytes[12:16], byteorder="little")

        msg = SubmitSharesSuccess(
            channel_id=channel_id,
            last_sequence_number=last_sequence_number,
            new_submits_accepted_count=new_submits_accepted_count,
            new_shares_sum=new_shares_sum,
        )
        return msg


class SubmitSharesError(ChannelMessage):
    def __init__(self, channel_id: int, sequence_number: int, error_code: str):
        self.sequence_number = sequence_number
        self.error_code = error_code
        super().__init__(channel_id)

    def __str__(self):
        return self._format(
            "channel_id={}, sequence_number={}, error_code={}".format(
                self.channel_id, self.sequence_number, self.error_code
            )
        )

    def to_bytes(self):
        channel_id = U32(self.channel_id)
        sequence_number = U32(self.sequence_number)
        error_code = STR0_255(self.error_code)

        payload = channel_id + sequence_number + error_code

        frame = FRAME(0x0, "SubmitSharesError", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        channel_id = int.from_bytes(bytes[:4], byteorder="little")
        sequence_number = int.from_bytes(bytes[4:8], byteorder="little")
        error_code_length = bytes[8]
        error_code = bytes[9 : 9 + error_code_length].decode("utf-8")

        msg = SubmitSharesError(
            channel_id=channel_id,
            sequence_number=sequence_number,
            error_code=error_code,
        )
        return msg


class NewMiningJob(ChannelMessage):
    def __init__(
        self,
        channel_id: int,
        job_id: int,
        future_job: bool,  # If is set to False, we MUST start to mine as soon as possible
        version: int,
        merkle_root: Hash,
    ):
        self.job_id = job_id
        self.future_job = future_job
        self.version = version
        self.merkle_root = merkle_root
        super().__init__(channel_id=channel_id)

    def __str__(self):
        return self._format(
            "channel_id={}, job_id={}, future_job={}, version={}, merkle_root={}".format(
                self.channel_id,
                self.job_id,
                self.future_job,
                self.version,
                self.merkle_root,
            )
        )

    def to_bytes(self):
        channel_id = U32(self.channel_id)
        job_id = U32(self.job_id)
        future_job = BOOL(self.future_job)
        version = U32(self.version)
        merkle_root = U32(self.merkle_root)

        payload = channel_id + job_id + future_job + version + merkle_root

        frame = FRAME(0x0, "NewMiningJob", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        channel_id = int.from_bytes(bytes[:4], byteorder="little")
        job_id = int.from_bytes(bytes[4:8], byteorder="little")
        future_job = bytes[8]
        version = int.from_bytes(bytes[9:13], byteorder="little")
        merkle_root = bytes[13:17]

        msg = NewMiningJob(
            channel_id=channel_id,
            job_id=job_id,
            future_job=future_job,
            version=version,
            merkle_root=merkle_root,
        )
        return msg


class SetNewPrevHash(ChannelMessage):
    def __init__(
        self, channel_id: int, job_id: int, prev_hash: Hash, min_ntime: int, nbits: int
    ):
        self.channel_id = channel_id
        self.prev_hash = prev_hash
        self.min_ntime = min_ntime
        self.nbits = nbits
        self.job_id = job_id
        super().__init__(channel_id)

    def __str__(self):
        return self._format(
            "channel_id={}, job_id={}, prev_hash={}, min_ntime={}, nbits={}".format(
                self.channel_id, self.job_id, self.prev_hash, self.min_ntime, self.nbits
            )
        )

    def to_bytes(self):
        channel_id = U32(self.channel_id)
        job_id = U32(self.job_id)
        prev_hash = U256(self.prev_hash)
        min_ntime = U32(self.min_ntime)
        nbits = U32(self.nbits)

        payload = channel_id + job_id + prev_hash + min_ntime + nbits

        frame = FRAME(0x0, "SetNewPrevHash", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        channel_id = int.from_bytes(bytes[:4], byteorder="little")
        job_id = int.from_bytes(bytes[4:8], byteorder="little")
        prev_hash = int.from_bytes(bytes[8:40], byteorder="little")
        min_ntime = int.from_bytes(bytes[40:44], byteorder="little")
        nbits = int.from_bytes(bytes[44:48], byteorder="little")

        msg = SetNewPrevHash(
            channel_id=channel_id,
            job_id=job_id,
            prev_hash=prev_hash,
            min_ntime=min_ntime,
            nbits=nbits,
        )
        return msg


class SetCustomMiningJob(ChannelMessage):
    def __init__(
        self,
        channel_id: int,
        request_id: int,
        mining_job_token: bytes,
        version: int,
        prev_hash: Hash,
        min_ntime: int,
        nbits: int,
        coinbase_tx_version: int,
        coinbase_prefix: bytes,
        coinbase_tx_input_nsequence: int,
        coinbase_tx_value_remaining: int,
        coinbase_tx_output: typing.Any,
        coinbase_tx_locktime: int,
        merkle_path: typing.Any,
        extranonce_size: int,
        future_job: bool,
    ):
        self.request_id = request_id
        self.mining_job_token = mining_job_token
        self.version = version
        self.prev_hash = prev_hash
        self.min_ntime = min_ntime
        self.nbits = nbits
        self.coinbase_tx_version = coinbase_tx_version
        self.coinbase_prefix = coinbase_prefix
        self.coinbase_tx_input_nsequence = coinbase_tx_input_nsequence
        self.coinbase_tx_value_remaining = coinbase_tx_value_remaining
        self.coinbase_tx_output = coinbase_tx_output
        self.coinbase_tx_locktime = coinbase_tx_locktime
        self.merkle_path = merkle_path
        self.extranonce_size = extranonce_size
        self.future_job = future_job
        super().__init__(channel_id=channel_id)


class SetCustomMiningJobSuccess(ChannelMessage):
    def __init__(
        self,
        channel_id: int,
        request_id: int,
        job_id: int,
        coinbase_tx_prefix: bytes,
        coinbase_tx_suffix: bytes,
    ):
        self.request_id = request_id
        self.job_id = job_id
        self.coinbase_tx_prefix = coinbase_tx_prefix
        self.coinbase_tx_suffix = coinbase_tx_suffix
        super().__init__(channel_id=channel_id)


class SetCustomMiningJobError(ChannelMessage):
    def __init__(self, channel_id: int, request_id: int, error_code: str):
        self.request_id = request_id
        self.error_code = error_code
        super().__init__(channel_id=channel_id)


class SetTarget(ChannelMessage):
    def __init__(self, channel_id: int, max_target: int):
        self.max_target = max_target
        super().__init__(channel_id=channel_id)

    def __str__(self):
        return self._format(
            "channel_id={}, max_target={}".format(self.channel_id, self.max_target)
        )

    def to_bytes(self):
        channel_id = U32(self.channel_id)
        max_target = U256(self.max_target)

        payload = channel_id + max_target

        frame = FRAME(0x0, "SetTarget", payload)
        return frame

    @staticmethod
    def from_bytes(bytes: bytearray):
        channel_id = int.from_bytes(bytes[:4], byteorder="little")
        max_target = int.from_bytes(bytes[4:8], byteorder="little")

        msg = SetTarget(
            channel_id=channel_id,
            max_target=max_target,
        )
        return msg


class Reconnect(Message):
    def __init__(self, new_host: str, new_port: int):
        self.new_host = new_host
        self.new_port = new_port
        super().__init__()


class SetGroupChannel(Message):
    def __init__(self, group_channel_id: int, channel_ids: typing.List):
        self.group_channel_id = group_channel_id
        self.channel_ids = channel_ids
        super().__init__()


# Extended and group channels only
class NewExtendedMiningJob(ChannelMessage):
    def __init__(
        self,
        channel_id: int,
        job_id: int,
        future_job: bool,
        version: int,
        version_rolling_allowed: bool,
        merkle_path: MerklePath,
        cb_prefix: CoinBasePrefix,
        cb_suffix: CoinBaseSuffix,
    ):
        self.job_id = job_id
        self.future_job = future_job
        self.version = version
        self.version_rolling_allowed = version_rolling_allowed
        self.merkle_path = merkle_path
        self.cb_prefix = cb_prefix
        self.cb_suffix = cb_suffix
        super().__init__(channel_id=channel_id)


msg_type_class_map = {
    0x00: SetupConnection,
    0x01: SetupConnectionSuccess,
    0x02: SetupConnectionError,
    0x10: OpenStandardMiningChannel,
    0x11: OpenStandardMiningChannelSuccess,
    0x1E: NewMiningJob,
    0x21: SetTarget,
    0x20: SetNewPrevHash,
    0x1A: SubmitSharesStandard,
    0x1C: SubmitSharesSuccess,
    0x1D: SubmitSharesError,
}
