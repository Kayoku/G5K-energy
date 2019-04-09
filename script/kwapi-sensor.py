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
Module Kwapi-sensor
"""

import argparse
import requests
import logging
import sys
import pymongo

LOGGER = logging.getLogger()
LOGGER.addHandler(logging.StreamHandler())

##############################################################################
# Useful functions
##############################################################################

def get_kwapi_url(city_name):
    """
    Return the url to JSON information available on g5k about Kwapi
    :param city_name: City name
    :return: URL of the node
    """
    return "https://api.grid5000.fr/stable/sites/"+city_name+"/metrics/power/"


def get_kwapi_value_url(city_name, node_name, timestamp_start, timestamp_stop):
    """
    Return the url to JSON information available on g5k about Kwapi series
    :param city_name: City name
    :param node_name: Node name
    :param timestamp_start: Timestamp to begin
    :param timestamp_stop: Timestamp to stop
    :return: URL of the node
    """
    return "https://api.grid5000.fr/stable/sites/"+city_name+"/metrics/power/timeseries?resolution=1&only="+node_name+"&from="+str(timestamp_start)+"&to="+str(timestamp_stop)


def is_kwapi_available(args):
    """
    Allow to know if Kwapi-sensor is available for this node
    :param args: Script argument
    :return: True if available, False otherwise
    """
    url = get_kwapi_url(args.city_name)
    request = requests.get(url,
                           auth=(args.g5k_login,
                                 args.g5k_pass),
                           verify=False)
    data = request.json()
    for node in data['available_on']:
        if args.node_name in node:
            return True
    return False


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

    # G5K informations
    parser.add_argument("g5k_login", help="G5K login")
    parser.add_argument("g5k_pass", help="G5K password")

    # MongoDB output
    parser.add_argument("mongodb_uri", help="MongoDB output uri")
    parser.add_argument("mongodb_db", help="MongoDB output database")
    parser.add_argument("mongodb_collection", help="MongoDB output collection")

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


def main():
    """
    Main function of the Kwapi-sensor
    """
    args = arg_parser_init().parse_args()

    # Test is Kwapi-sensor can monitor this node
    if not is_kwapi_available(args):
        LOGGER.error("Kwapi-sensor not available for the node " + args.node_name)
        sys.exit(-1)

    output = connect_mongodb(args)
    url = get_kwapi_value_url(args.city_name,
                              args.node_name,
                              args.timestamp_start,
                              args.timestamp_stop)
    data = requests.get(url,
                        auth=(args.g5k_login,
                              args.g5k_pass),
                        verify=False).json()

    # If there is no data, -1 everywhere
    if len(data['items']) > 0:
        offset = 0
        for ts in range(int(args.timestamp_start), int(args.timestamp_stop)):
            # If offset is outofrange or
            #    data timestamp is different from the current ts
            if (offset >= len(data['items'][0]['timestamps']) or
                    ts != data['items'][0]['timestamps'][offset]):
                continue
            new_row = create_data(ts, "kwapi-sensor", data['items'][0]['values'][offset])
            output.insert_one(new_row)
            offset += 1


if __name__ == "__main__":
    main()
