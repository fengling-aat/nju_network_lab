'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
import switchyard
from switchyard.lib.userlib import *
import time

def main(net: switchyard.llnetbase.LLNetBase):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]
    lst = {}
    while True:
        try:
            _, fromIface, packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            break
        log_debug (f"In {net.name} received packet {packet} on {fromIface}")
        eth = packet.get_header(Ethernet)
        #{mac_addr:[port,traffic]}
        port = my_interfaces[0]
        for intf in my_interfaces:
            if(fromIface == intf.name):
                port = intf
                break

        if eth.src in lst:
            if port != lst[eth.src][0]:
                lst[eth.src][0] = port
            #lst[eth.src][1] += 1
        else:
            if(len(lst) == 5):
                min_addr = min(lst,key = lambda k:lst[k][1])
                del lst[min_addr]
            lst[eth.src] = [port,0]    
        
        if eth is None:
            log_info("Received a non-Ethernet packet?!")
            return
        if eth.dst in mymacs:
            log_info("Received a packet intended for me")
        else:
            if eth.dst in lst.keys():
                intf = lst[eth.dst][0]
                lst[eth.dst][1] += 1
                net.send_packet(intf,packet)
            else:
                for intf in my_interfaces:
                    if fromIface!= intf.name:
                        log_info (f"Flooding packet {packet} to {intf.name}")
                        net.send_packet(intf, packet)

    net.shutdown()
