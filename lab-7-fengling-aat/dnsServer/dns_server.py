'''DNS Server for Content Delivery Network (CDN)
'''

import sys
from socketserver import UDPServer, BaseRequestHandler
from utils.dns_utils import DNS_Request, DNS_Rcode
from utils.ip_utils import IP_Utils
from datetime import datetime
from random import choice
import math

import re

from collections import namedtuple


__all__ = ["DNSServer", "DNSHandler"]

def match(str1,str2):
    temp1 = str1
    temp2 = str2
    if str1[len(str1)-1] == '.':
        temp1 = str1[:len(str1)-1]
    if str2[len(str2)-1] == '.':
        temp2 = str2[:len(str2)-1]
    print(temp1,temp2)
    if temp1[0] != '*':
        return temp1 == temp2
    else:
        idx = temp2.find('.')
        return temp1[1:] == temp2[idx:]

class DNSServer(UDPServer):
    def __init__(self, server_address, dns_file, RequestHandlerClass, bind_and_activate=True):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate=True)
        self._dns_table = []
        self.parse_dns_file(dns_file)
        
    def parse_dns_file(self, dns_file):
        # ---------------------------------------------------
        # TODO: your codes here. Parse the dns_table.txt file
        # and load the data into self._dns_table.
        # --------------------------------------------------
        f = open('./dnsServer/dns_table.txt')
        line = f.readline()
        while(line):
            line = line[:len(line)-1]
            line = line.split(' ')
            print(line)
            self._dns_table.append(line)
            line = f.readline()
        f.close()

    @property
    def table(self):
        return self._dns_table


class DNSHandler(BaseRequestHandler):
    """
    This class receives clients' udp packet with socket handler and request data. 
    ----------------------------------------------------------------------------
    There are several objects you need to mention:
    - udp_data : the payload of udp protocol.
    - socket: connection handler to send or receive message with the client.
    - client_ip: the client's ip (ip source address).
    - client_port: the client's udp port (udp source port).
    - DNS_Request: a dns protocl tool class.
    We have written the skeleton of the dns server, all you need to do is to select
    the best response ip based on user's infomation (i.e., location).

    NOTE: This module is a very simple version of dns server, called global load ba-
          lance dns server. We suppose that this server knows all the ip addresses of 
          cache servers for any given domain_name (or cname).
    """
    
    def __init__(self, request, client_address, server):
        self.table = server.table
        super().__init__(request, client_address, server)

    def calc_distance(self, pointA, pointB):
        ''' TODO: calculate distance between two points '''
        return (pointA[0]-pointB[0])**2 + (pointA[1]-pointB[1])**2

    def get_response(self, request_domain_name):
        response_type, response_val = (None, None)
        # ------------------------------------------------
        # TODO: your codes here.
        # Determine an IP to response according to the client's IP address.
        #       set "response_ip" to "the best IP address".
        client_ip, _ = self.client_address
        
        print("domain:",request_domain_name)

        for item in self.table:
            print(item)
            #if re.search(item[0],request_domain_name):
            if match(item[0],request_domain_name):
                response_type = item[1]
                if len(item) == 3:
                    response_val = item[2]
                elif len(item) > 3:
                    candidate = item[2:len(item)]
                    if IP_Utils.getIpLocation(client_ip) == None:
                        response_val = choice(candidate)
                    else:
                        ip_paddr = IP_Utils.getIpLocation(client_ip)
                        distance = self.calc_distance(ip_paddr,IP_Utils.getIpLocation(candidate[0]))
                        response_val = candidate[0]
                        for item in candidate[1:]:
                            if self.calc_distance(ip_paddr,IP_Utils.getIpLocation(item)) < distance:
                                distance = self.calc_distance(ip_paddr,IP_Utils.getIpLocation(item))
                                response_val = item
                break

        # -------------------------------------------------
        return (response_type, response_val)

    def handle(self):
        """
        This function is called once there is a dns request.
        """
        ## init udp data and socket.
        udp_data, socket = self.request

        ## read client-side ip address and udp port.
        client_ip, client_port = self.client_address

        ## check dns format.
        valid = DNS_Request.check_valid_format(udp_data)
        if valid:
            ## decode request into dns object and read domain_name property.
            dns_request = DNS_Request(udp_data)
            request_domain_name = str(dns_request.domain_name)
            self.log_info(f"Receving DNS request from '{client_ip}' asking for "
                          f"'{request_domain_name}'")

            # get caching server address
            response = self.get_response(request_domain_name)

            # response to client with response_ip
            if None not in response:
                dns_response = dns_request.generate_response(response)
            else:
                dns_response = DNS_Request.generate_error_response(
                                             error_code=DNS_Rcode.NXDomain)
        else:
            self.log_error(f"Receiving invalid dns request from "
                           f"'{client_ip}:{client_port}'")
            dns_response = DNS_Request.generate_error_response(
                                         error_code=DNS_Rcode.FormErr)

        socket.sendto(dns_response.raw_data, self.client_address)

    def log_info(self, msg):
        self._logMsg("Info", msg)

    def log_error(self, msg):
        self._logMsg("Error", msg)

    def log_warning(self, msg):
        self._logMsg("Warning", msg)

    def _logMsg(self, info, msg):
        ''' Log an arbitrary message.
        Used by log_info, log_warning, log_error.
        '''
        info = f"[{info}]"
        now = datetime.now().strftime("%Y/%m/%d-%H:%M:%S")
        sys.stdout.write(f"{now}| {info} {msg}\n")
