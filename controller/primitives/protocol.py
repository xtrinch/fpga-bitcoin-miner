"""Generic protocol primitives"""
import stringcase
from abc import abstractmethod

import simpy
from event_bus import EventBus

from primitives.connection import Connection
from primitives.messages import (
msg_type_class_map, 
SubmitSharesStandard, 
SetupConnection, 
SetupConnectionSuccess, 
SetupConnectionError, 
Message, 
OpenStandardMiningChannel, 
NewMiningJob, SetTarget, 
SetNewPrevHash, 
OpenStandardMiningChannelSuccess)
import asyncio # new module 

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
        self.receive_loop_process = self.env.process(self.receive_loop())

    def terminate(self):
        self.receive_loop_process.interrupt()

    def send_request(self, req):
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
        self.bus.emit(self.name, self.env.now, self.connection.uid, log_msg)

    def _emit_protocol_msg_on_bus(self, log_msg: str, msg: Message):
        print(msg)
        self._emit_aux_msg_on_bus('{}: {}'.format(log_msg, msg))

    def receive_one(self):
        # Receive process for a particular connection dispatches each received message
        try:
            # TODO: make this so it doesn't ahve to check
            if self.connection.conn_target:
                ciphertext = self.connection.conn_target.recv(8192)
            else:
                ciphertext = self.connection.sock.recv(8192)
            
            if not ciphertext:
                raise Exception('Closed connection')
            
            frame, _ = Connection.unwrap(ciphertext)
            
            # print(frame)
            raw = self.connection.decrypt_cipher_state.decrypt_with_ad(b'', frame)
            
    
            # plaintext is a frame
            extension_type = raw[0:1]
            msg_type = raw[2]
            msg_length = raw[3:5] #U24
    
            # TODO: find a more concise way of doing this
            print(msg_type)
            msg = None
            raw = raw[6:] # remove the common bytes
            
            msg_class = msg_type_class_map[msg_type]
            msg = msg_class.from_bytes(raw)
            # if msg_type == 0x00:
            #     msg = SetupConnection.from_bytes(raw)
            # elif msg_type == 0x01:
            #     msg = SetupConnectionSuccess.from_bytes(raw)
            # elif msg_type == 0x02:
            #     msg = SetupConnectionError.from_bytes(raw)
            # elif msg_type == 0x10:
            #     msg = OpenStandardMiningChannel.from_bytes(raw)
            # elif msg_type == 0x11:
            #     msg = OpenStandardMiningChannelSuccess.from_bytes(raw)
            # elif msg_type == 0x1e:
            #     msg = NewMiningJob.from_bytes(raw)
            # elif msg_type == 0x21:
            #     msg = SetTarget.from_bytes(raw)
            # elif msg_type == 0x20:
            #     msg = SetNewPrevHash.from_bytes(raw)
                
            print('receive msg %s' % msg)

            try:
                msg.accept(self)
            except Message.VisitorMethodNotImplemented as e:
                print(
                    "{} doesn't implement:{}() for".format(type(self).__name_, e),
                    msg,
                )
        except simpy.Interrupt:
            print('DISCONNECTED')
                        
    async def receive_loop(self):
        """Receive process for a particular connection dispatches each received message
        """
        while True:
            try:
                self.receive_one()
            except Exception as e:
                print(e)
                await asyncio.sleep(2.5)
                continue
