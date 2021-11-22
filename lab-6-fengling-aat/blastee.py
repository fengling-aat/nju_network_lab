#!/usr/bin/env python3

import time
import threading
from struct import pack
from typing import Sequence
import switchyard
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *


class Blastee:
    def __init__(
            self,
            net: switchyard.llnetbase.LLNetBase,
            blasteeIp,
            num
    ):
        self.net = net
        # TODO: store the parameters
        self.Ip = blasteeIp
        self.num = int(num)

    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        _, fromIface, packet = recv
        log_debug(f"I got a packet from {fromIface}")
        log_debug(f"Pkt: {packet}")
        #print(packet[3])
        ack = Ethernet() + IPv4(protocol=IPProtocol.UDP) + UDP()
        ack[0].src = '20:00:00:00:00:01'
        ack[0].dst = '40:00:00:00:00:02'
        ack[1].src = '192.168.200.1'
        ack[1].dst = '192.168.100.1'
        ack[1].ttl = 10
        sequence = packet[3].to_bytes()[:4]
        #payload = packet[3].to_bytes[6:14]
        ack += sequence
        length = int.from_bytes(packet[3].to_bytes()[4:6], byteorder = 'big')
        if length < 8:
            ack += packet[3].to_bytes()[6:]
            ack += (0).to_bytes(8 - length, byteorder = "big")
        else:
            ack += packet[3].to_bytes()[6:14]
        self.net.send_packet(fromIface,ack)

    def start(self):
        '''A running daemon of the blastee.
        Receive packets until the end of time.
        '''
        while True:
            try:
                recv = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                continue
            except Shutdown:
                break

            self.handle_packet(recv)

        self.shutdown()

    def shutdown(self):
        self.net.shutdown()


def main(net, **kwargs):
    blastee = Blastee(net, **kwargs)
    blastee.start()
