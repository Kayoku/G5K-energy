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
import signal
import time
import logging
import sys
import datetime
import asyncio
import pymongo
import socket
from execo_g5k import get_host_attributes
from pysnmp.hlapi.asyncio import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectIdentity, ObjectType

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.StreamHandler())

##############################################################################
# Useful functions
##############################################################################


def is_snmp_available(args):
    """
    Allow to know if SNMP-sensor is available for this node
    :param args: Script argument
    :return: True if available, False otherwise
    """
    try:
        data = get_host_attributes(args.node_name)
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
    data = get_host_attributes(args.node_name)

    # Get PDU name
    pdus_name = [pdu['uid'] for pdu in data['sensors']['power']['via']['pdu']]

    # Get PDU IP/port
    pdus_infos = []
    for pdu_name in pdus_name:
        port = None
        for pdu_info in data['sensors']['power']['via']['pdu']:
            if pdu_info['uid'] == pdu_name:
                port = pdu_info['port']
                break
        ip = socket.gethostbyname(pdu_name+"."+args.city_name+".grid5000.fr")
        pdus_infos.append((pdu_name, ip, port))

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


def connect_mongodb(args):
    """
    Return the collection to write the output
    :param args: Script arguments
    :return: MongoDB collection
    """
    mongo_client = pymongo.MongoClient(args.mongodb_uri,
                                       serverSelectionTimeoutMS=5)
    collection = mongo_client[args.mongodb_db][args.mongodb_collection]

    # Check if it work
    try:
        mongo_client.admin.command('ismaster')
    except pymongo.errors.ServerSelectionTimeoutError:
        LOGGER.error("MongoDB error.")
        exit(-1)

    return collection


def create_data(timestamp, sensor, power):
    """
    Create the Dict with data
    :param timestamp: Timestamp int
    :param sensor: Sensor name
    :param power: Power value
    :return: Dict data
    """
    return {
        "timestamp": timestamp,
        "sensor": sensor,
        "power": power
    }

##############################################################################
# Parser
##############################################################################


def arg_parser_init():
    """
    Initialize argument parser
    """
    parser = argparse.ArgumentParser(
        description="Start PowerAPI with the specified configuration.")

    # MongoDB output
    parser.add_argument("mongodb_uri", help="MongoDB output uri")
    parser.add_argument("mongodb_db", help="MongoDB output database")
    parser.add_argument("mongodb_collection", help="MongoDB output collection")

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
    LOGGER.warning("/!\ This script is not compatible with python 3.7 /!\\")

    # Test is SNMP-sensor can monitor this node
    if not is_snmp_available(args):
        LOGGER.error("SNMP-sensor not available for the node " + args.node_name)
        sys.exit(-1)

    # Signal handling
    def term_handler(_, __):
        LOGGER.warning("Ended by user.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, term_handler)
    signal.signal(signal.SIGINT, term_handler)

    # Get the MongoDB
    output = connect_mongodb(args)

    # Get the tuple IP/port of each necessary PDU
    pdus_infos = get_pdu_ip_and_port(args)

    # Run loop
    loop = asyncio.get_event_loop()
    next_ts = 0
    while True:
        tasks = []

        for pdu_info in pdus_infos:
            tasks.append(asyncio.async(run_watt(pdu_info[1], pdu_info[2])))

        loop.run_until_complete(asyncio.wait(tasks))

        ts = 0
        value = 0
        for t in tasks:
            res = t.result()
            if res[0] is None and res[1] is None:
                LOGGER.warning("Loose connection with SNMP node.")
                exit(-1)
            ts = res[1]
            value += res[0]

        new_data = create_data(ts, "snmp-sensor", value)
        if next_ts < new_data["timestamp"]:
            LOGGER.info(new_data)
            output.insert_one(new_data)
            next_ts = new_data["timestamp"]

    loop.close()


if __name__ == "__main__":
    main()
