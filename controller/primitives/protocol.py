"""Generic protocol primitives"""
import asyncio  # new module
import socket
from abc import abstractmethod

import simpy
import stringcase
from colorama import Back, Cursor, Fore, Style
from event_bus import EventBus

from primitives.connection import Connection
from primitives.messages import (
    Message,
    NewMiningJob,
    OpenStandardMiningChannel,
    OpenStandardMiningChannelSuccess,
    SetNewPrevHash,
    SetTarget,
    SetupConnection,
    SetupConnectionError,
    SetupConnectionSuccess,
    SubmitSharesStandard,
    msg_type_class_map,
)


class RequestRegistry:
    """Generates unique request ID for messages and provides simple registry"""

    def __init__(self):
        self.next_req_id = 0
        self.requests = dict()

    def push(self, req: Message):
        """Assigns a unique request ID to a message and registers it"""
        req.req_id = self.__next_req_id()
        assert (
            self.requests.get(req.req_id) is None
        ), "BUG: request ID already present {}".format(req.req_id)
        self.requests[req.req_id] = req

    def pop(self, req_id):
        return self.requests.pop(req_id, None)

    def __next_req_id(self):
        curr_req_id = self.next_req_id
        self.next_req_id += 1
        return curr_req_id


class ConnectionProcessor:
    """Receives and dispatches a message on a single connection."""

    def __init__(self, name: str, bus: EventBus, connection: Connection):
        self.name = name
        self.bus = bus
        self.connection = connection
        self.request_registry = RequestRegistry()
        self.receive_loop_process = None

    def terminate(self):
        self.receive_loop_process.interrupt()

    def send_request(self, req):
        self.request_registry.push(req)
        self.connection.send_msg(req)

    @abstractmethod
    def _send_msg(self, msg):
        pass

    @abstractmethod
    def _recv_msg(self):
        pass

    @abstractmethod
    def _on_invalid_message(self, msg):
        pass

    def _emit_aux_msg_on_bus(self, log_msg: str):
        print(("{}: {}").format(self.name, log_msg))

    def _emit_protocol_msg_on_bus(self, log_msg: str, msg: Message):
        self._emit_aux_msg_on_bus("{}: {}".format(log_msg, msg))

    def receive_one(self):
        # Receive process for a particular connection dispatches each received message
        # TODO: make this so it doesn't ahve to check
        if self.connection.conn_target:
            ciphertext = self.connection.conn_target.recv(8192)
        else:
            ciphertext = self.connection.sock.recv(8192)

        if not ciphertext:
            raise socket.timeout("Closed connection")

        print("ciphertext")
        print(ciphertext)

        frame, _ = Connection.unwrap(ciphertext)

        raw = self.connection.decrypt_cipher_state.decrypt_with_ad(b"", frame)

        print("raw")
        print(raw)
        # plaintext is a frame
        extension_type = raw[0:1]
        msg_type = raw[2]
        msg_length = raw[3:5]  # U24

        # TODO: find a more concise way of doing this
        msg = None
        raw = raw[6:]  # remove the common bytes

        msg_class = msg_type_class_map[msg_type]
        msg = msg_class.from_bytes(raw)

        print(
            f"{Style.BRIGHT}{Fore.YELLOW}Msg rcv: {Style.NORMAL}%s{Style.RESET_ALL}"
            % msg
        )

        try:
            msg.accept(self)
        except Message.VisitorMethodNotImplemented as e:
            print(
                "{} doesn't implement:{}() for".format(type(self).__name_, e),
                msg,
            )

    async def receive_loop(self):
        """Receive process for a particular connection dispatches each received message"""
        while True:
            try:
                self.receive_one()
            except socket.timeout as e:
                print(e)
                await asyncio.sleep(0)
                continue
