import json
import time
import requests
import argparse
import math
from typing import Optional

from pyproj import Transformer

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
        ret.tablerotation = data["spatial"]["rotation"]

        proj = Transformer.from_crs(getFromCfg("input_crs"), getFromCfg("compute_crs"))
        ret.origin = proj.transform(data["spatial"]["latitude"], data["spatial"]["longitude"])
        return ret

    def updateGrid(self, endpoint=-1, token=None):
        self.grid = getCurrentState("grid", endpoint, token)

    def Local2Geo(self, x, y):
        bearing = self.tablerotation

        x *= self.cellSize
        y *= -self.cellSize  # flip y axis (for northern hemisphere)

        # rotate and scale
        new_x = x * math.cos(math.radians(bearing)) - y * math.sin(math.radians(bearing))
        new_y = x * math.sin(math.radians(bearing)) + y * math.cos(math.radians(bearing))

        # convert to geo coords
        return (new_x + self.origin[0], new_y + self.origin[1])


def getFromCfg(key: str) -> str:
    # import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]


def getCurrentState(topic="", endpoint=-1, token=None):
    if endpoint == -1 or endpoint == None:
        get_address = getFromCfg("input_url") + topic
    else:
        get_address = getFromCfg("input_urls")[endpoint] + topic

    try:
        if token is None:
            r = requests.get(get_address, headers={'Content-Type': 'application/json'})
        else:
            r = requests.get(get_address, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+token})
        
        if not r.status_code == 200:
            print("could not get from cityIO")
            print("Error code", r.status_code)
            return {}

        return r.json()
    
    except requests.exceptions.RequestException as e:
        print("CityIO error while GETting!" + e)
        return {}

def sendToCityIO(data, endpoint=-1, token=None):
    if endpoint == -1 or endpoint == None:
        post_address = getFromCfg("output_url")
    else:
        post_address = getFromCfg("output_urls")[endpoint]

    try:
        if token is None:
            r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json'})
        else:
            r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+token})
        print(r)
        if not r.status_code == 200:
            print("could not post result to cityIO", post_address)
            print("Error code", r.status_code)
        else:
            print("Successfully posted to cityIO", post_address, r.status_code)

    except requests.exceptions.RequestException as e:
        print("CityIO error while POSTing!" + e)
        return


def remove_empty_cells_from_geojson(geojson):
    geojson['features'] = [feature for feature in geojson['features'] if not feature['properties'] == {}]

def writeFile(filepath, data):
    f= open(filepath,"w+")
    f.write(data)

def run(endpoint=-1, token=None):
    gridDef = Table.fromCityIO(getCurrentState("header", endpoint, token))
    if not gridDef:
        print("couldn't load input_url!")
        exit()

    gridData = getCurrentState("grid", endpoint, token)
    gridHash = getCurrentState("meta/hashes/grid", endpoint, token)
    geojson = json.loads(makeGeoJSON(gridData, gridDef))

    typejs = {}
    with open("typedefs.json") as file:
        typejs = json.load(file)

    bld_living = 0
    bld_commerce = 0
    bld_special = 0
    os_green = 0
    os_sports = 0
    os_play = 0

    for cell_id, cell in enumerate(gridData):
        if (cell is None or not "type" in gridDef.mapping[cell[gridDef.typeidx]]): continue
        curtype = gridDef.mapping[cell[gridDef.typeidx]]["type"]

        if curtype == "building":

            curuse1 = gridDef.mapping[cell[gridDef.typeidx]]["bld_useGround"]
            curusen = gridDef.mapping[cell[gridDef.typeidx]]["bld_useUpper"]
            curlevels = gridDef.mapping[cell[gridDef.typeidx]]["bld_numLevels"]

            geojson['features'][cell_id]['properties'] = {
               "bld_useGround": curuse1,
               "bld_useUpper": curusen,
               "bld_numLevels": curlevels
           }

            # ground floor uses
            if curuse1 and curlevels > 0:
                if curuse1 in typejs["buildinguses"]["living"]:
                    bld_living += gridDef.cellSize * gridDef.cellSize
                if curuse1 in typejs["buildinguses"]["commerce"]:
                    bld_commerce += gridDef.cellSize * gridDef.cellSize
                if curuse1 in typejs["buildinguses"]["special"]:
                    bld_special += gridDef.cellSize * gridDef.cellSize
            # upper floor uses
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

    remove_empty_cells_from_geojson(geojson)

    data = {"living": bld_living, "living_expected": 400000,
            "commerce": bld_commerce, "commerce_expected": 550000,
            "special": bld_special, "special_expected": 30000,
            "green": os_green, "green_expected": 80000,
            "sports": os_sports, "sports_expected": 10000,
            "playgrounds": os_play, "playgrounds_expected": 10000,
            "geojson": geojson,
            "grid_hash": gridHash}
    # writeFile("test.json",json.dumps(geojson))
    sendToCityIO(data, endpoint, token)


def makeGeoJSON(gridData, cityio):
    resultjson = "{\"type\": \"FeatureCollection\",\"features\": [" # geojson front matter

    # append features for all grid cells
    resultjson += appendPointFeatures(gridData, cityio)

    resultjson += "]}" # geojson end matter
    return resultjson

def appendPointFeatures(gridData, cityio):
    filledGrid = list(gridData)
    resultjson = ""

    proj = Transformer.from_crs(getFromCfg("compute_crs"), getFromCfg("output_crs"))
    for idx in range(len(filledGrid)):
        x = idx % cityio.ncols
        y = idx // cityio.ncols

        properties = {}

        centerPoint = cityio.Local2Geo((x + 0.5),(y + 0.5)) # upper left
        centerPoint = proj.transform(centerPoint[1],centerPoint[0])

        resultjson += PolyToGeoJSON(centerPoint, idx, properties) # append feature, closes loop
        resultjson +=","

    resultjson = resultjson[:-1] # trim trailing comma
    return resultjson


def PolyToGeoJSON(point, id, properties):

    ret = "{\"type\": \"Feature\",\"id\": \""
    ret += str(id)
    ret += "\",\"geometry\": {\"type\": \"Point\",\"coordinates\": ["

    ret += str(point[1]) + "," + str(point[0])

    ret += "]},"
    ret += "\"properties\": {"
    for key in properties: # properties to string
        ret += "\""+key+"\""
        ret += ":"
        ret += str(properties[key])
        ret += ","
    if len(properties) > 0:
        ret=ret[:-1] # delete trailing comma after properties
    ret += "}}"
    return ret

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculate KPIs on cityIO according to Grasbrook Auslobung.')
    parser.add_argument('--endpoint', type=int, default=-1, help="endpoint url to choose from config.ini/input_urls")
    args = parser.parse_args()
    print("endpoint", args.endpoint)

    token = None
    # try:
    #     with open("token.txt") as f:
    #         token = f.readline()
    #     if token == "": token = None  # happens with empty file
    # except IOError:
    #     token = None

    oldHash = ""

    while True:
        gridHash = getCurrentState("meta/hashes/grid", int(args.endpoint), token)
        if gridHash != {} and gridHash != oldHash:
            run(int(args.endpoint), token)
            oldHash = gridHash
        else:
            print("waiting for grid change")
            time.sleep(5)
