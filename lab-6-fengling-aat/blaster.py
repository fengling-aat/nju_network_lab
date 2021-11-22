#!/usr/bin/env python3

import time
from random import randint
import switchyard
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *

class mission:
    def __init__(self) -> None:
        self.is_acked = 0
        self.is_sent = 0

class Blaster:
    def __init__(
            self,
            net: switchyard.llnetbase.LLNetBase,
            blasterIp,
            num,
            length="100",
            senderWindow="5",
            timeout="10",
            recvTimeout="100"
    ):
        self.net = net
        # TODO: store the parameters
        self.blasterIp = blasterIp
        self.num = int(num)
        self.length = int(length)
        self.sw = int(senderWindow)
        self.timeout = int(timeout)
        self.recv_to = int(recvTimeout)
        self.lhs = self.rhs = 1
        self.begintime = self.endtime = -1
        self.ack_num = 0
        self.timer = time.time()
        self.queue = []
        self.re_tranmit_num = 0
        self.num_timeout = 0
        self.output_byte = 0
        self.good_put = 0
        self.last_seq = -1
        for i in range(0,self.num+1):
            self.queue.append(mission())

    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        _, fromIface, packet = recv
        #print("I got a packet")
        sequence = packet[3].to_bytes()[:4]
        seq = int.from_bytes(sequence,'big')
        print("ack ",seq)
        if self.queue[seq].is_acked == 0:
            self.good_put += self.length
            self.queue[seq].is_acked = 1
            self.ack_num += 1
        if self.ack_num == self.num:
            self.endtime = time.time()
        i = 1
        while i < self.num+1 and self.queue[i].is_acked == 1:
            i += 1
        if i > self.lhs:
            self.lhs = i
            if self.lhs > self.rhs:
                self.rhs = self.lhs
            self.timer = time.time()

    def process_pkt(self,pkt,seq):
        pkt[0].src = '10:00:00:00:00:01'
        pkt[0].dst = '40:00:00:00:00:01'
        pkt[1].src = '192.168.100.1'
        pkt[1].dst = '192.168.200.1'
        pkt[1].ttl = 10
        data = seq.to_bytes(4, 'big')
        data += self.length.to_bytes(2, 'big')
        pkt+= data
        payload = b'data ddata dddata ddddata dddddata'
        payload = payload[0:self.length-1]
        pkt += payload

    def handle_no_packet(self):
        print("Didn't receive anything")
        print("RHS:",self.rhs," LHS",self.lhs)
        # Creating the headers for the packet
        pkt = Ethernet() + IPv4() + UDP()
        pkt[1].protocol = IPProtocol.UDP
        if time.time() - self.timer > self.timeout:
            self.re_tranmit_num += 1
            if self.last_seq != self.lhs:
                self.last_seq = self.lhs
                self.num_timeout += 1
            self.process_pkt(pkt,self.lhs)
            self.output_byte += self.length
            self.net.send_packet("blaster-eth0",pkt)
            print(self.lhs," timeout resend")
            #self.timer = time.time()
        if self.rhs - self.lhs < 5 and self.rhs <= self.num:
            if self.queue[self.rhs].is_sent == 0:
                if self.rhs == 1 and self.begintime == -1:
                    self.begintime = time.time()
                self.process_pkt(pkt,self.rhs)
                print("send ",self.rhs)
                self.output_byte += self.length
                self.net.send_packet("blaster-eth0",pkt)
                self.queue[self.rhs].is_sent = 1
                #self.queue[self.rhs].timer = time.time()
                if self.rhs - self.lhs < 4 and self.rhs < self.num:
                    self.rhs += 1
            elif self.rhs - self.lhs < 4 and self.rhs < self.num:
                self.rhs += 1


    def start(self):
        '''A running daemon of the blaster.
        Receive packets until the end of time.
        '''
        while True:
            try:
                recv = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                self.handle_no_packet()
                continue
            except Shutdown:
                break

            self.handle_packet(recv)
            if self.ack_num == self.num:
                break

        self.shutdown()

    def shutdown(self):
        self.net.shutdown()


def main(net, **kwargs):
    blaster = Blaster(net, **kwargs)
    blaster.start()
    total_time = blaster.endtime-blaster.begintime
    print(blaster.endtime,"  ",blaster.begintime,"s")
    print("total time:",round(total_time,2))
    print("number of retx:" ,blaster.re_tranmit_num)
    print("number of coarse to:",blaster.num_timeout)
    print("throughput(bps):",round(blaster.output_byte/total_time,2),"bps")
    print("goodput(bps):",round(blaster.good_put/total_time,2),"bps")
    
