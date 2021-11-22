#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import time
import switchyard
from switchyard.lib.userlib import *
from switchyard.lib.address import *

from_intf : str

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
        #print([pkt,intf,nextip,time,0])
        self.queue.insert(0,[pkt,intf,nextip,time,0])

    def send(self,arp):
        print("here")
        ip = arp.senderprotoaddr
        mac = arp.senderhwaddr
        for item in self.queue:
            if ip == item[2]:
                print(item)
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
            #print(item)
            pkt = item[0]
            intf = item[1]
            next_ip = item[2]
            t = item[3]
            num = item[4]
            #print(intf.name,next_ip,t,num)
            if next_ip in self.arptable.keys():
                print("hhhh",item[2])
                print(item)
                eth_index = pkt.get_header_index(Ethernet)
                pkt[eth_index].dst = self.arptable[next_ip]
                pkt[eth_index].src = intf.ethaddr
                ipv4 = pkt.get_header(IPv4)
                print(ipv4.src,ipv4.dst)
                self.net.send_packet(intf.name,pkt)  
                print("successfully sended")
                self.queue.remove(item)
            elif time.time() - t > 1.0:
                print(num)
                if num >= 5:
                    print(pkt)
                    if pkt.get_header_index(ICMP)!= -1:
                        global from_intf
                        print(from_intf)
                        ip = self.net.interface_by_name(from_intf).ipaddr
                        ipv4 = pkt.get_header(IPv4)
                        pkt = self.build_icmp(ICMPType.DestinationUnreachable,1,pkt,ip,ipv4.src,len(pkt))
                        src_index = self.match(ipv4.src)
                        self.process_pkt(src_index,pkt,ipv4.src)
                        #self.insert(pkt,self.net.interface_by_name(from_intf),ipv4.src,time.time())
                    self.queue.remove(item)
                    #self.del_queue.append(item)
                else:
                    print(item)
                    ether = Ethernet()
                    ether.src = intf.ethaddr
                    ether.dst = "ff:ff:ff:ff:ff:ff"
                    ether.ethertype = EtherType.ARP
                    arp = Arp(operation=ArpOperation.Request,
                            senderhwaddr=intf.ethaddr,
                            senderprotoaddr=intf.ipaddr,
                            targethwaddr='ff:ff:ff:ff:ff:ff',
                            targetprotoaddr=next_ip)
                    arppacket = ether+arp
                    item[3] = time.time()
                    item[4] += 1
                    print(intf.name,item[2])
                    print(arppacket)
                    self.net.send_packet(intf.name,arppacket)
                    print("finish request")
                    

    def build_icmp(self,Type,Code,pkt,Src,Dst,length):
        print("nonetype1")
        i = pkt.get_header_index(Ethernet)
        del pkt[i]
        icmp = ICMP()
        icmp.icmptype = Type
        icmp.icmpcode = Code
        icmp.icmpdata.data = pkt.to_bytes()[:28]
        icmp.icmpdata.origdgramlen = length
        ip = IPv4()
        ip.protocol = IPProtocol.ICMP
        ip.ttl = 10
        ip.src = Src
        ip.dst = Dst
        #return Ethernet() + ip + icmp
        return Ethernet() + ip + icmp


    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        self.display()
        timestamp, ifaceName, packet = recv
        # TODO: your logic here
        global from_intf
        from_intf = ifaceName
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
            eth = packet[Ethernet]
            if eth.ethertype != EtherType.IPv4:
                return
            packet[ipdx].ttl -= 1
            print(packet[ipdx].ttl)
            ipv4 = packet[ipdx]
            icmp_idx = packet.get_header_index(ICMP)
            Dst = ipv4.src
            print(Dst)
            Src = self.net.interface_by_name(ifaceName).ipaddr
            length = len(packet)
            src_index = self.match(ipv4.src)
            dst_index = self.match(ipv4.dst)
            #process icmp
            if ipv4.dst in [intf.ipaddr for intf in self.interfaces]:
                if icmp_idx != -1 and packet[icmp_idx].icmptype == ICMPType.EchoRequest:
                    #dst is this router
                    i = ICMP()
                    i.icmptype = ICMPType.EchoReply
                    i.icmpdata.sequence = packet[icmp_idx].icmpdata.sequence
                    i.icmpdata.identifier = packet[icmp_idx].icmpdata.identifier
                    i.icmpdata.data = packet[icmp_idx].icmpdata.data
                    ipv4.dst,ipv4.src = ipv4.src,ipv4.dst
                    packet[icmp_idx] = i
                    self.process_pkt(src_index,packet,ipv4.dst)
                    return
                else:
                    #index = self.match(ipv4.src)
                    packet = self.build_icmp(ICMPType.DestinationUnreachable,3,packet,Src,Dst,length)
                    self.process_pkt(src_index,packet,Dst)
                    return
            elif packet[ipdx].ttl == 0:
                #ttl = 0
                packet = self.build_icmp(ICMPType.TimeExceeded,0,packet,Src,Dst,length)
                #self.insert(packet,self.net.interface_by_name(ifaceName),Dst,time.time())
                self.process_pkt(src_index,packet,Dst)
                return

            elif dst_index != -1:
                #match in forwarding table
                self.process_pkt(dst_index,packet,ipv4.dst)
                return
            else:
                #no match in forwarding table
                packet = self.build_icmp(ICMPType.DestinationUnreachable,0,packet,Src,Dst,length)
                self.insert(packet,self.net.interface_by_name(ifaceName),Dst,time.time())
                return

    #dstip in forwarding table        
    def process_pkt(self,index,packet,dstip):
        global from_intf
        if index == -1:
            return
        next_ip = self.ftable[index][1]
        if next_ip == IPv4Address('0.0.0.0'):
            next_ip = dstip
        print(next_ip)
        print(self.ftable[index][2])
        if next_ip in self.arptable.keys():
            intfname = self.ftable[index][2]
            intf = self.net.interface_by_name(intfname)
            mac = self.arptable[next_ip]
            eth_index = packet.get_header_index(Ethernet)
            packet[eth_index].src = intf.ethaddr
            packet[eth_index].dst = mac 
            self.net.send_packet(intfname, packet)
        else:
            print(next_ip)
            self.insert(packet,self.net.interface_by_name(self.ftable[index][2]),next_ip,time.time())

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