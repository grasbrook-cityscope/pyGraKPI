import json
import time
import requests
import argparse
from typing import Optional


class Table:
    cellSize = 0
    ncols = 0
    nrows = 0

    @staticmethod
    def fromCityIO(data):
        ret = Table()
        ret.cellSize = data["spatial"]["cellSize"]
        ret.ncols = data["spatial"]["ncols"]
        ret.nrows = data["spatial"]["nrows"]
        ret.mapping = data["mapping"]["type"]
        ret.typeidx = data["block"].index("type")
        return ret


def getFromCfg(key: str) -> str:
    # import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]


# returns the token for the endpoint
# tokens.json is to be requested from admin
def getToken(endpoint=-1) -> Optional[str]:
    if endpoint == -1:
        return None

    with open("tokens.json") as file:
        js = json.load(file)
        return js['tokens'][endpoint]


def getCurrentState(topic="", endpoint=-1, token=None):
    if endpoint == -1 or endpoint == None:
        get_address = getFromCfg("input_url") + topic
    else:
        get_address = getFromCfg("input_urls")[endpoint] + topic

    if token is None:
        r = requests.get(get_address, headers={'Content-Type': 'application/json'})
    else:
        r = requests.get(get_address, headers={'Content-Type': 'application/json',
                                               'Authorization': 'Bearer {}'.format(token).rstrip()})

    if not r.status_code == 200:
        print("could not get from cityIO")
        print("Error code", r.status_code)
        return {}

    return r.json()


def sendToCityIO(data, endpoint=-1, token=None):
    if endpoint == -1 or endpoint == None:
        post_address = getFromCfg("output_url")
    else:
        post_address = getFromCfg("output_urls")[endpoint]

    if token is None:
        r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json'})
    else:
        r = requests.post(post_address, json=data,
                          headers={'Content-Type': 'application/json',
                                   'Authorization': 'Bearer {}'.format(token).rstrip()})
    print(r)
    if not r.status_code == 200:
        print("could not post result to cityIO", post_address)
        print("Error code", r.status_code)
    else:
        print("Successfully posted to cityIO", post_address, r.status_code)


def run(endpoint=-1, token=None):
    gridDef = Table.fromCityIO(getCurrentState("header", endpoint, token))
    if not gridDef:
        print("couldn't load input_url!")
        exit()

    gridData = getCurrentState("grid", endpoint, token)
    gridHash = getCurrentState("meta/hashes/grid", endpoint, token)

    typejs = {}
    with open("typedefs.json") as file:
        typejs = json.load(file)

    bld_living = 0
    bld_commerce = 0
    bld_special = 0
    os_green = 0
    os_sports = 0
    os_play = 0

    for cell in gridData:
        if (cell is None or not "type" in gridDef.mapping[cell[gridDef.typeidx]]): continue
        curtype = gridDef.mapping[cell[gridDef.typeidx]]["type"]

        if curtype == "building":
            curuse1 = gridDef.mapping[cell[gridDef.typeidx]]["bld_useGround"]
            curusen = gridDef.mapping[cell[gridDef.typeidx]]["bld_useUpper"]
            curlevels = gridDef.mapping[cell[gridDef.typeidx]]["bld_numLevels"]

            if curuse1 and curlevels > 0:
                if curuse1 in typejs["buildinguses"]["living"]:
                    bld_living += gridDef.cellSize * gridDef.cellSize
                if curuse1 in typejs["buildinguses"]["commerce"]:
                    bld_commerce += gridDef.cellSize * gridDef.cellSize
                if curuse1 in typejs["buildinguses"]["special"]:
                    bld_special += gridDef.cellSize * gridDef.cellSize

            if curusen and curlevels > 1:
                if curusen in typejs["buildinguses"]["living"]:
                    bld_living += gridDef.cellSize * gridDef.cellSize * (curlevels - 1)
                if curusen in typejs["buildinguses"]["commerce"]:
                    bld_commerce += gridDef.cellSize * gridDef.cellSize * (curlevels - 1)
                if curusen in typejs["buildinguses"]["special"]:
                    bld_special += gridDef.cellSize * gridDef.cellSize * (curlevels - 1)

        elif curtype == "open_space":
            curuse = gridDef.mapping[cell[gridDef.typeidx]]["os_type"]
            if curuse in typejs["openspacetypes"]["green"]:
                os_green += gridDef.cellSize * gridDef.cellSize
            if curuse in typejs["openspacetypes"]["sports"]:
                os_sports += gridDef.cellSize * gridDef.cellSize
            if curuse in typejs["openspacetypes"]["playgrounds"]:
                os_play += gridDef.cellSize * gridDef.cellSize

    data = {"living": bld_living, "living_expected": 400000,
            "commerce": bld_commerce, "commerce_expected": 550000,
            "special": bld_special, "special_expected": 30000,
            "green": os_green, "green_expected": 80000,
            "sports": os_sports, "sports_expected": 10000,
            "playgrounds": os_play, "playgrounds_expected": 10000,
            "grid_hash": gridHash}

    print(data)

    sendToCityIO(data, endpoint, token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculate KPIs on cityIO according to Grasbrook Auslobung.')
    parser.add_argument('--endpoint', type=int, default=-1, help="endpoint url to choose from config.ini/input_urls")
    args = parser.parse_args()
    print("endpoint", args.endpoint)
    token = getToken(args.endpoint)

    oldHash = ""

    while True:
        gridHash = getCurrentState("meta/hashes/grid", int(args.endpoint), token)
        if gridHash != {} and gridHash != oldHash:
            run(int(args.endpoint), token)
            oldHash = gridHash
        else:
            print("waiting for grid change")
            time.sleep(5)
