import json
import urllib.request 
import time

def getFromCfg(key : str) -> str:
    #import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]

def getCurrentState(topic=""):
    with urllib.request.urlopen(getFromCfg("input_url")+topic) as url:    # todo: do with requests instead of urllib
        return json.loads(url.read().decode())
    return None

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

def sendToCityIO(data):
    post_address = getFromCfg("output_url")

    import requests
    r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json'})
    print(r)
    if not r.status_code == 200:
        print("could not post result to cityIO")
        print("Error code", r.status_code)
    else:
        print("Successfully posted to cityIO", r.status_code)

def run():
    gridDef = Table.fromCityIO(getCurrentState("header"))
    if not gridDef:
        print("couldn't load input_url!")
        exit()

    gridData = getCurrentState("grid")
    gridHash = getCurrentState("meta/hashes/grid")

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
        if(cell is None or not "type" in gridDef.mapping[cell[gridDef.typeidx]]): continue
        curtype = gridDef.mapping[cell[gridDef.typeidx]]["type"]

        if curtype == "building":
            curuse1 = gridDef.mapping[cell[gridDef.typeidx]]["bld_useGround"]
            curusen = gridDef.mapping[cell[gridDef.typeidx]]["bld_useUpper"]
            curlevels = gridDef.mapping[cell[gridDef.typeidx]]["bld_numLevels"]

            if curuse1 and curlevels > 0:
                if curuse1 in typejs["buildinguses"]["living"]:
                    bld_living += gridDef.cellSize*gridDef.cellSize
                if curuse1 in typejs["buildinguses"]["commerce"]:
                    bld_commerce += gridDef.cellSize*gridDef.cellSize
                if curuse1 in typejs["buildinguses"]["special"]:
                    bld_special += gridDef.cellSize*gridDef.cellSize

            if curusen and curlevels > 1:
                if curusen in typejs["buildinguses"]["living"]:
                    bld_living += gridDef.cellSize*gridDef.cellSize * (curlevels - 1)
                if curuse1 in typejs["buildinguses"]["commerce"]:
                    bld_commerce += gridDef.cellSize*gridDef.cellSize * (curlevels - 1)
                if curuse1 in typejs["buildinguses"]["special"]:
                    bld_special += gridDef.cellSize*gridDef.cellSize * (curlevels - 1)
        
        elif curtype == "open_space":
            curuse = gridDef.mapping[cell[gridDef.typeidx]]["os_type"]
            if curuse in typejs["openspacetypes"]["green"]:
                os_green += gridDef.cellSize*gridDef.cellSize
            if curuse in typejs["openspacetypes"]["sports"]:
                os_sports += gridDef.cellSize*gridDef.cellSize
            if curuse in typejs["openspacetypes"]["playgrounds"]:
                os_play += gridDef.cellSize*gridDef.cellSize

    data = {"living":bld_living, "living_expected":400000,
            "commerce":bld_commerce, "commerce_expected":550000,
            "special":bld_special, "special_expected":30000,
            "green":os_green,"green_expected":80000,
            "sports":os_sports,"sports_expected":10000,
            "playgrounds":os_play,"playgrounds_expected":10000,
            "grid_hash":gridHash}

    print(data)

    sendToCityIO(data)
    

if __name__ == "__main__":
    oldHash = ""

    while True:
        gridHash = getCurrentState("meta/hashes/grid")
        if gridHash != oldHash:
            run()
            oldHash = gridHash
        else:
            print("waiting for grid change")
            time.sleep(10)