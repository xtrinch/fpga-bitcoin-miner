"""Generic protocol primitives"""
import stringcase
from abc import abstractmethod

import simpy
from event_bus import EventBus

from primitives.connection import Connection
from primitives.messages import SetupConnection, SetupConnectionSuccess, Message

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
        ), 'BUG: request ID already present {}'.format(req.req_id)
        self.requests[req.req_id] = req

    def pop(self, req_id):
        return self.requests.pop(req_id, None)

    def __next_req_id(self):
        curr_req_id = self.next_req_id
        self.next_req_id += 1
        return curr_req_id


class ConnectionProcessor:
    """Receives and dispatches a message on a single connection."""

    def __init__(
        self, name: str, env: simpy.Environment, bus: EventBus, connection: Connection
    ):
        self.name = name
        self.env = env
        self.bus = bus
        self.connection = connection
        self.request_registry = RequestRegistry()
        self.receive_loop_process = self.env.process(self.__receive_loop())

    def terminate(self):
        self.receive_loop_process.interrupt()

    def send_request(self, req):
        """Register the request and send it down the line"""
        self.request_registry.push(req)
        self._send_msg(req)

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
        self.bus.emit(self.name, self.env.now, self.connection.uid, log_msg)

    def _emit_protocol_msg_on_bus(self, log_msg: str, msg: Message):
        self._emit_aux_msg_on_bus('{}: {}'.format(log_msg, msg))

    def receive_one(self):
        # Receive process for a particular connection dispatches each received message
        print("RCV one?")
        try:
            raw = self.connection.sock.recv(4096)
            msg = SetupConnectionSuccess.from_bytes(raw)
            print('INCOMING', msg)

            try:
                msg.accept(self)
            except Message.VisitorMethodNotImplemented as e:
                print(
                    "{} doesn't implement:{}() for".format(type(self).__name_, e),
                    msg,
                )
        except simpy.Interrupt:
            print('DISCONNECTED')
            
    def __receive_loop(self):
        """Receive process for a particular connection dispatches each received message
        """
        while True:
            print("RCV loop")
            try:
                msg = yield self.env.process(self._recv_msg())
                self._emit_protocol_msg_on_bus('INCOMING', msg)

                try:
                    msg.accept(self)
                except Message.VisitorMethodNotImplemented as e:
                    self._emit_protocol_msg_on_bus(
                        "{} doesn't implement:{}() for".format(type(self).__name_, e),
                        msg,
                    )
                #    self._on_invalid_message(msg)

            except simpy.Interrupt:
                self._emit_aux_msg_on_bus('DISCONNECTED')
                break  # terminate the event loop
