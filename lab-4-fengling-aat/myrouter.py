#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import time
import switchyard
from switchyard.lib.userlib import *
from switchyard.lib.address import *


class Router(object):
    def __init__(self, net: switchyard.llnetbase.LLNetBase):
        self.net = net
        self.arptable = {}
        self.interfaces = self.net.interfaces()
        self.ftable = []
        self.queue = []
        self.del_queue = []
        # other initialization stuff here

    def match(self,ipaddr):
        #print(ipaddr)
        index = -1
        length = 0
        ipaddrs = [intf.ipaddr for intf in self.interfaces]
        if ipaddr not in ipaddrs:
            #print("dst not in intf")
            i = 0
            while i < len(self.ftable):
                if ipaddr in self.ftable[i][0] and self.ftable[i][0].prefixlen > length:
                    #print(i)
                    #rint(self.ftable[i][0].prefixlen)
                    #print(self.ftable[i][0])
                    index = i
                    length = self.ftable[i][0].prefixlen
                i = i + 1
            #log_info(self.ftable[index][0])
            #log_info(self.ftable[index][1])
            #log_info(self.ftable[index][2])
            #
            # print(index)
        return index

    def insert(self,pkt,intf,nextip,time):
        self.queue.append([pkt,intf,nextip,time,0])

    def send(self,arp):
        ip = arp.senderprotoaddr
        mac = arp.senderhwaddr
        for item in self.queue:
            if ip == item[2]:
                packet = item[0]
                intf = item[1]
                eth_index = packet.get_header_index(Ethernet)
                packet[eth_index].src = intf.ethaddr
                packet[eth_index].dst = mac
                self.net.send_packet(item[1].name,packet)
                self.queue.remove(item)

    def forward(self):
        #print("11")
        for item in self.queue:
            pkt = item[0]
            intf = item[1]
            next_ip = item[2]
            t = item[3]
            num = item[4]
            #print(intf.name,next_ip,t,num)
            if next_ip in self.arptable.keys():
                eth_index = pkt.get_header_index(Ethernet)
                pkt[eth_index].dst = self.arptable[next_ip]
                self.net.send_packet(intf.name,pkt)  
                self.queue.remove(item)
            elif time.time() - t > 1.0:
                if num >= 5:
                    self.queue.remove(item)
                    #self.del_queue.append(item)
                else:
                    ether = Ethernet()
                    ether.src = intf.ethaddr
                    ether.dst = "ff:ff:ff:ff:ff:ff"
                    ether.ethertype = EtherType.ARP
                    arp = Arp(operation=ArpOperation.Request,
                            senderhwaddr=intf.ethaddr,
                            senderprotoaddr=intf.ipaddr,
                            targethwaddr='ff:ff:ff:ff:ff:ff',
                            targetprotoaddr=next_ip)
                    packet = ether+arp
                    item[3] = time.time()
                    item[4] += 1
                    self.net.send_packet(intf.name,packet)
                    



    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        timestamp, ifaceName, packet = recv
        # TODO: your logic here
        arp = packet.get_header(Arp)
        ipdx = packet.get_header_index(IPv4)
        #print("1")
        if(arp):
            #print("2")
            self.arptable[arp.senderprotoaddr] = arp.senderhwaddr
            for key,value in self.arptable.items():
                print(key,":",value)
            print(" ")
            if arp.operation == ArpOperation.Request:
                #print("4")
                for intf in self.interfaces:
                    if(arp.targetprotoaddr == intf.ipaddr):
                        Packet = create_ip_arp_reply(intf.ethaddr, arp.senderhwaddr, intf.ipaddr, arp.senderprotoaddr)
                        self.net.send_packet(ifaceName,Packet)
            elif arp.operation == ArpOperation.Reply:
                self.send(arp)
        
        elif(ipdx != -1):
            #print("3")
            packet[ipdx].ttl -= 1
            ipv4 = packet[ipdx]
            index = self.match(ipv4.dst)
            if index == -1:
                #print("5")
                pass
            else:
                #print("6")
                next_ip = self.ftable[index][1]
                intfname = self.ftable[index][2]
                #print(next_ip,intfname)
                intf = self.net.interface_by_name(intfname)
                if next_ip == IPv4Address('0.0.0.0'):
                        #print("9")
                    next_ip = ipv4.dst
                if next_ip == intf.ipaddr:
                    #print("7")
                    pass
                else:
                    #print("8")
                    #if next_ip == IPv4Address('0.0.0.0'):
                        #print("9")
                        #next_ip = ipv4.dst
                    if next_ip in self.arptable.keys():
                        #print(10)
                        mac = self.arptable[next_ip]
                        eth_index = packet.get_header_index(Ethernet)
                        packet[eth_index].src = intf.ethaddr
                        packet[eth_index].dst = mac 
                        #print(self.ftable[index][1])
                        self.net.send_packet(intfname, packet)
                    else:
                        #print("12")
                        self.insert(packet,intf,next_ip,time.time())
        #self.del_queue = []               
        #self.forward()
        #for item in self.del_queue:
            #self.queue.remove(item)


    def build(self):
        for intf in self.interfaces:
            p = []
            p.append(IPv4Network(str(intf.ipaddr) + '/' + str(intf.netmask),False))
            p.append(IPv4Address("0.0.0.0"))
            p.append(intf.name)
            self.ftable.append(p)
        with open("forwarding_table.txt","r") as f:
            for item in f:
                p = []
                l = len(item) - 1
                if(item[l] == '\n'):
                    item = item[:l]
                data = item.split(" ",4)
                p.append(IPv4Network(data[0] + "/" + data[1]))
                p.append(IPv4Address(data[2]))
                p.append(data[3])
                self.ftable.append(p)

    def display(self):
        for item in self.ftable:
            print(item)

    def start(self):
        '''A running daemon of the router.
        Receive packets until the end of time.
        '''
        self.build()
        for item in self.ftable:
            log_info(item)
        while True:
            #self.del_queue = []  
            self.forward()
            #for item in self.del_queue:
                #self.queue.remove(item)
            try:
                recv = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                continue
            except Shutdown:
                break

            self.handle_packet(recv)             

        self.stop()

    def stop(self):
        self.net.shutdown()


def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    router = Router(net)
    router.start()