# Copyright (C) 2018  University of Lille
# Copyright (C) 2018  INRIA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module SNMP-sensor
"""

import argparse
import requests
import time
import logging
import sys
import datetime
import asyncio
from pysnmp.hlapi.asyncio import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectIdentity, ObjectType

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.StreamHandler())

##############################################################################
# Useful functions
##############################################################################


def get_node_url(city_name, cluster_name, node_name):
    """
    Return the url to JSON information available on g5k about this node
    :param city_name: City name
    :param cluster_name: Cluster name
    :param node_name: Node name
    :return: URL of the node
    """
    return "https://api.grid5000.fr/stable/sites/"+city_name+"/clusters/"+cluster_name+"/nodes/"+node_name+".json"


def get_pdu_url(city_name, pdu_name):
    """
    Return the url to JSON information available on g5k about this pdu
    :param city_name: City name
    :param pdu_name: PDU name
    :return: URL of the node
    """
    return "https://api.grid5000.fr/stable/sites/"+city_name+"/pdus/"+pdu_name+".json"


def is_snmp_available(args):
    """
    Allow to know if SNMP-sensor is available for this node
    :param args: Script argument
    :return: True if available, False otherwise
    """
    url = get_node_url(args.city_name, args.cluster_name, args.node_name)
    try:
        request = requests.get(url,
                               auth=(args.g5k_login,
                                     args.g5k_pass),
                               verify=False)
        data = request.json()
        data['sensors']['power']['via']['pdu']
    except KeyError:
        return False
    return True


def get_pdu_ip_and_port(args):
    """
    Return the PDU IP String, and the port associate to the current Node
    :param args: Script argument
    :return: List of PDU with IP/port
    """
    url = get_node_url(args.city_name, args.cluster_name, args.node_name)
    request = requests.get(url,
                           auth=(args.g5k_login,
                                 args.g5k_pass),
                           verify=False)
    data = request.json()

    # Get PDU name
    pdus_name = [pdu['uid'] for pdu in data['sensors']['power']['via']['pdu']]

    # Get PDU IP/port
    pdus_infos = []
    for pdu_name in pdus_name:
        pdu_url = get_pdu_url(args.city_name, pdu_name)
        pdu_request = requests.get(pdu_url,
                                   auth=(args.g5k_login,
                                         args.g5k_pass),
                                   verify=False)
        pdu_data = pdu_request.json()

        port = None
        for key_port, value_node_name in pdu_data['ports'].items():
            if value_node_name == args.node_name:
                port = key_port
                break
        pdus_infos.append((pdu_name, pdu_data['ip'], port))

    return pdus_infos


@asyncio.coroutine
def run_watt(pdu_ip, pdu_node_port):
    snmpEngine = SnmpEngine()
    errorIndication, errorStatus, errorIndex, varBinds = yield from getCmd(
        snmpEngine,
        CommunityData('public', mpModel=1),
        UdpTransportTarget((pdu_ip, 161)),
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.4.1.318.1.1.26.9.4.3.1.7.'+str(pdu_node_port))),
        ObjectType(ObjectIdentity('1.3.6.1.4.1.318.2.1.6.1.0')),
        ObjectType(ObjectIdentity('1.3.6.1.4.1.318.2.1.6.2.0'))
    )

    watt = None
    timestamp = None

    if errorIndication:
        LOGGER.error(errorIndication)
    elif errorStatus:
        LOGGER.error('%s at %s' % (
            errorStatus.prettyPrint(),
            errorIndex and varBinds[int(errorIndex) - 1][0] or '?'
        ))
    else:
        watt = int(varBinds[0][1])
        timestamp_str = str(varBinds[1][1]) + " "+ str(varBinds[2][1])
        timestamp = int(time.mktime(datetime.datetime.strptime(timestamp_str, "%m/%d/%Y %H:%M:%S").timetuple()))

    snmpEngine.transportDispatcher.closeDispatcher()

    return watt, timestamp


##############################################################################
# Parser
##############################################################################


def arg_parser_init():
    """
    Initialize argument parser
    """
    parser = argparse.ArgumentParser(
        description="Start PowerAPI with the specified configuration.")

    # G5K informations
    parser.add_argument("g5k_login", help="G5K login")
    parser.add_argument("g5k_pass", help="G5K password")

    # MongoDB output
    #parser.add_argument("output_uri", help="MongoDB output uri")
    #parser.add_argument("output_db", help="MongoDB output database")
    #parser.add_argument("output_collection", help="MongoDB output collection")

    # Node informations
    parser.add_argument("city_name", help="City name where the cluster is")
    parser.add_argument("cluster_name", help="Cluster name where the node is")
    parser.add_argument("node_name", help="Node name to monitor")

    return parser

##############################################################################
# Main
##############################################################################


def main():
    """
    Main function of the SNMP-sensor
    """
    args = arg_parser_init().parse_args()

    LOGGER.warning("/!\ Make sure you are in the G5K network /!\\")
    LOGGER.warning("This script is written for working with python 3.5.")

    # Test is SNMP-sensor can monitor this node
    if not is_snmp_available(args):
        LOGGER.error("SNMP-sensor not available for the node " + args.node_name)
        sys.exit(-1)

    # Get the tuple IP/port of each necessary PDU
    pdus_infos = get_pdu_ip_and_port(args)

    # Run loop
    loop = asyncio.get_event_loop()
    history = {}
    while True:

        tasks = []

        for pdu_info in pdus_infos:
            tasks.append(asyncio.async(run_watt(pdu_info[1], pdu_info[2])))

        loop.run_until_complete(asyncio.wait(tasks))

        ts = 0
        value = 0
        for t in tasks:
            res = t.result()
            ts = res[1]
            value += res[0]
        history[ts] = value
        LOGGER.warning("Break")
        LOGGER.warning(history)

    loop.close()


if __name__ == "__main__":
    main()
