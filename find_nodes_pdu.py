"""
Module use to find all pdu link to nodes
"""
import urllib.request
import json
import sys

NODES = {
    "grenoble": ("dahu", 32),
    "lyon": ("nova", 23),
    "lille": ("chetemi", 15),
    "nantes": ("ecotype", 48),
    "nancy": ("grisou", 51),
    "rennes": ("paravance", 72)
}

if len(sys.argv) != 2:
    print("Need to specify password")
    exit(1)

def setup():
    # create a password manager
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()

    # Add the username and password.
    # If we knew the realm, we could use it instead of None.
    top_level_url = "https://api.grid5000.fr/"
    password_mgr.add_password(None, top_level_url, "jbouchoucha", sys.argv[1])

    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

    # create "opener" (OpenerDirector instance)
    opener = urllib.request.build_opener(handler)

    # use the opener to fetch a URL
    opener.open("https://api.grid5000.fr")

    # Install the opener.
    # Now all calls to urllib.request.urlopen use our opener.
    urllib.request.install_opener(opener)

def find_key(key, search_dict):
    res = None
    for n_key, n_values in search_dict.items():
        if n_key == key:
            return n_values

        if isinstance(n_values, dict):
            res = find_key(key, n_values)

        if res is not None:
            return res
    return None


def get_node_url(city, cluster, node):
    """
    Return the url for node information.

    :param str city: City name
    :param str cluster: Cluster name
    :param str node: Node name
    :return str: Url
    """
    return "https://api.grid5000.fr/stable/sites/%s/clusters/%s/nodes/%s.json" % (city, cluster, node)


setup()

for city in NODES:
    node_name = NODES[city][0]
    node_size = NODES[city][1]

    for node_id in range(1, node_size+1):
        node_url = get_node_url(city, node_name, node_name+"-"+str(node_id))
        with urllib.request.urlopen(node_url) as url:
            data = json.loads(url.read().decode())
            print("%s %s-%s: %s" % (city, node_name, node_id, find_key("pdu", data)))
