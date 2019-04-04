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
Module Omegawatt-sensor
"""

import argparse
import requests
import time
import logging
import sys
import datetime
import gzip
import numpy as np
from execo_g5k import get_host_attributes

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.StreamHandler())

##############################################################################
# Useful functions
##############################################################################


def get_omegawatt_url(city_name):
    """
    Return the url to JSON information available on g5k about omegawatt
    :param city_name: City name
    :return: URL of the node
    """
    return "http://wattmetre."+city_name+".grid5000.fr/GetWatts-json.php"


def is_omegawatt_available(args):
    """
    Allow to know if Omegawatt-sensor is available for this node
    :param args: Script argument
    :return: True if available, False otherwise
    """
    # City in ["grenoble", "lyon"]
    # http://wattmetre.<CITY>.grid5000.fr/GetWatts-json.php
    # Browse JSON dict and found "NODE_NAME"
    if args.city_name not in ['grenoble', 'lyon']:
        return False

    url = get_omegawatt_url(args.city_name)
    data = requests.get(url).json()
    for node in data.items():
        if args.node_name in node:
            return True
    return False


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
    #parser.add_argument("output_uri", help="MongoDB output uri")
    #parser.add_argument("output_db", help="MongoDB output database")
    #parser.add_argument("output_collection", help="MongoDB output collection")

    # Node informations
    parser.add_argument("city_name", help="City name where the cluster is")
    parser.add_argument("cluster_name", help="Cluster name where the node is")
    parser.add_argument("node_name", help="Node name to monitor")

    # Timestamp information
    parser.add_argument("timestamp_start", help="Timestamp where begin the series")
    parser.add_argument("timestamp_stop", help="Timestamp where end the series")

    return parser

##############################################################################
# Main
##############################################################################

def parse_omegawatt(args):
    """
    source: https://gitlab.inria.fr/delamare/wattmetre-read/raw/master/tools/getwatt.py
    :param args: Script argument
    :return: A list of (timestamp, value) tuples.
    """

    watt = {}
    node_wattmetre = get_host_attributes(args.node_name)['sensors']['power']['via']['pdu'][0]
    from_ts = int(args.timestamp_start)
    to_ts = int(args.timestamp_stop)

    for ts in range(from_ts, to_ts+3600, 3600):
        suffix = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H')
        if suffix != datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H'):
            suffix += ".gz"
        req = requests.get("http://wattmetre."+args.city_name+".grid5000.fr/data/"+node_wattmetre['uid']+"-log/power.csv."+suffix)
        if req.status_code == 404:
            return watt
        data = req.content
        if suffix.endswith(".gz"):
            data = gzip.decompress(data)
        for l in str(data).split('\\n')[1:-1]:
            l = l.split(',')
            if l[3] == 'OK' and l[4+node_wattmetre['port']] != '':
                ts, value = (int(np.round(float(l[2]))), float(l[4+node_wattmetre['port']]))
                if from_ts <= ts and ts <= to_ts:
                    if ts not in watt:
                        watt[ts] = [0, 0]
                    watt[ts][0] += value
                    watt[ts][1] += 1
        if not suffix.endswith(".gz"):
            break

    for ts, val in watt.items():
        watt[ts] = watt[ts][0] / watt[ts][1]
    return watt


def main():
    """
    Main function of the Omegawatt-sensor
    """
    args = arg_parser_init().parse_args()
    LOGGER.warning("/!\ Make sure you are in the G5K network /!\\")

    if not is_omegawatt_available(args):
        LOGGER.error("Omegawatt-sensor not available for the node " + args.node_name)
        sys.exit(-1)

    res = {"timestamps": [x for x in range(int(args.timestamp_start), int(args.timestamp_stop)+1)],
           "values": []}
    data = parse_omegawatt(args)

    for ts in res['timestamps']:
        # If offset is outofrange or
        #    data timestamp is different from the current ts
        if ts not in data:
            res['values'].append(-1)
            continue

        res['values'].append(data[ts])

    print(res)


if __name__ == "__main__":
    main()
