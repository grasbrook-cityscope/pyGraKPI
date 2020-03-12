import json
import time
import requests
import argparse
import math
from typing import Optional

from pyproj import CRS, Proj
from pyproj._transformer import _Transformer
from pyproj.compat import cstrencode
from pyproj.enums import TransformDirection, WktVersion
from pyproj.exceptions import ProjError
from pyproj.utils import _convertback, _copytobuffer

class Transformer(object):
    """
    The Transformer class is for facilitating re-using
    transforms without needing to re-create them. The goal
    is to make repeated transforms faster.

    Additionally, it provides multiple methods for initialization.
    """

    def __init__(self, base_transformer=None):
        if not isinstance(base_transformer, _Transformer):
            ProjError.clear()
            raise ProjError(
                "Transformer must be initialized using: "
                "'from_crs', 'from_pipeline', or 'from_proj'."
            )
        self._transformer = base_transformer

    @property
    def name(self):
        """
        str: Name of the projection.
        """
        return self._transformer.id

    @property
    def description(self):
        """
        str: Description of the projection.
        """
        return self._transformer.description

    @property
    def definition(self):
        """
        str: Definition of the projection.
        """
        return self._transformer.definition

    @property
    def has_inverse(self):
        """
        bool: True if an inverse mapping exists.
        """
        return self._transformer.has_inverse

    @property
    def accuracy(self):
        """
        float: Expected accuracy of the transformation. -1 if unknown.
        """
        return self._transformer.accuracy

    @staticmethod
    def from_proj(proj_from, proj_to, skip_equivalent=False, always_xy=False):
        """Make a Transformer from a :obj:`~pyproj.proj.Proj` or input used to create one.

        Parameters
        ----------
        proj_from: :obj:`~pyproj.proj.Proj` or input used to create one
            Projection of input data.
        proj_to: :obj:`~pyproj.proj.Proj` or input used to create one
            Projection of output data.
        skip_equivalent: bool, optional
            If true, will skip the transformation operation if input and output
            projections are equivalent. Default is false.
        always_xy: bool, optional
            If true, the transform method will accept as input and return as output
            coordinates using the traditional GIS order, that is longitude, latitude
            for geographic CRS and easting, northing for most projected CRS.
            Default is false.

        Returns
        -------
        :obj:`~Transformer`

        """
        if not isinstance(proj_from, Proj):
            proj_from = Proj(proj_from)
        if not isinstance(proj_to, Proj):
            proj_to = Proj(proj_to)

        return Transformer(
            _Transformer.from_crs(
                proj_from.crs,
                proj_to.crs,
                skip_equivalent=skip_equivalent,
                always_xy=always_xy,
            )
        )

    @staticmethod
    def from_crs(crs_from, crs_to, skip_equivalent=False, always_xy=False):
        """Make a Transformer from a :obj:`~pyproj.crs.CRS` or input used to create one.

        Parameters
        ----------
        crs_from: ~pyproj.crs.CRS or input used to create one
            Projection of input data.
        crs_to: ~pyproj.crs.CRS or input used to create one
            Projection of output data.
        skip_equivalent: bool, optional
            If true, will skip the transformation operation if input and output
            projections are equivalent. Default is false.
        always_xy: bool, optional
            If true, the transform method will accept as input and return as output
            coordinates using the traditional GIS order, that is longitude, latitude
            for geographic CRS and easting, northing for most projected CRS.
            Default is false.

        Returns
        -------
        :obj:`~Transformer`

        """
        transformer = Transformer(
            _Transformer.from_crs(
                CRS.from_user_input(crs_from),
                CRS.from_user_input(crs_to),
                skip_equivalent=skip_equivalent,
                always_xy=always_xy,
            )
        )
        return transformer

    @staticmethod
    def from_pipeline(proj_pipeline):
        """Make a Transformer from a PROJ pipeline string.

        https://proj.org/operations/pipeline.html

        Parameters
        ----------
        proj_pipeline: str
            Projection pipeline string.

        Returns
        -------
        ~Transformer

        """
        return Transformer(_Transformer.from_pipeline(cstrencode(proj_pipeline)))

    def transform(
        self,
        xx,
        yy,
        zz=None,
        tt=None,
        radians=False,
        errcheck=False,
        direction=TransformDirection.FORWARD,
    ):
        """
        Transform points between two coordinate systems.

        Parameters
        ----------
        xx: scalar or array (numpy or python)
            Input x coordinate(s).
        yy: scalar or array (numpy or python)
            Input y coordinate(s).
        zz: scalar or array (numpy or python), optional
            Input z coordinate(s).
        tt: scalar or array (numpy or python), optional
            Input time coordinate(s).
        radians: boolean, optional
            If True, will expect input data to be in radians and will return radians
            if the projection is geographic. Default is False (degrees). Ignored for
            pipeline transformations.
        errcheck: boolean, optional (default False)
            If True an exception is raised if the transformation is invalid.
            By default errcheck=False and an invalid transformation
            returns ``inf`` and no exception is raised.
        direction: ~pyproj.enums.TransformDirection, optional
            The direction of the transform.
            Default is :attr:`~pyproj.enums.TransformDirection.FORWARD`.


        Example:

        >>> from pyproj import Transformer
        >>> transformer = Transformer.from_crs("epsg:4326", "epsg:3857")
        >>> x3, y3 = transformer.transform(33, 98)
        >>> "%.3f  %.3f" % (x3, y3)
        '10909310.098  3895303.963'
        >>> pipeline_str = (
        ...     "+proj=pipeline +step +proj=longlat +ellps=WGS84 "
        ...     "+step +proj=unitconvert +xy_in=rad +xy_out=deg"
        ... )
        >>> pipe_trans = Transformer.from_pipeline(pipeline_str)
        >>> xt, yt = pipe_trans.transform(2.1, 0.001)
        >>> "%.3f  %.3f" % (xt, yt)
        '120.321  0.057'
        >>> transproj = Transformer.from_crs(
        ...     {"proj":'geocent', "ellps":'WGS84', "datum":'WGS84'},
        ...     "EPSG:4326",
        ...     always_xy=True,
        ... )
        >>> xpj, ypj, zpj = transproj.transform(
        ...     -2704026.010,
        ...     -4253051.810,
        ...     3895878.820,
        ...     radians=True,
        ... )
        >>> "%.3f %.3f %.3f" % (xpj, ypj, zpj)
        '-2.137 0.661 -20.531'
        >>> transprojr = Transformer.from_crs(
        ...     "EPSG:4326",
        ...     {"proj":'geocent', "ellps":'WGS84', "datum":'WGS84'},
        ...     always_xy=True,
        ... )
        >>> xpjr, ypjr, zpjr = transprojr.transform(xpj, ypj, zpj, radians=True)
        >>> "%.3f %.3f %.3f" % (xpjr, ypjr, zpjr)
        '-2704026.010 -4253051.810 3895878.820'
        >>> transformer = Transformer.from_proj("epsg:4326", 4326, skip_equivalent=True)
        >>> xeq, yeq = transformer.transform(33, 98)
        >>> "%.0f  %.0f" % (xeq, yeq)
        '33  98'

        """
        # process inputs, making copies that support buffer API.
        inx, xisfloat, xislist, xistuple = _copytobuffer(xx)
        iny, yisfloat, yislist, yistuple = _copytobuffer(yy)
        if zz is not None:
            inz, zisfloat, zislist, zistuple = _copytobuffer(zz)
        else:
            inz = None
        if tt is not None:
            intime, tisfloat, tislist, tistuple = _copytobuffer(tt)
        else:
            intime = None
        # call pj_transform.  inx,iny,inz buffers modified in place.
        self._transformer._transform(
            inx,
            iny,
            inz=inz,
            intime=intime,
            direction=direction,
            radians=radians,
            errcheck=errcheck,
        )
        # if inputs were lists, tuples or floats, convert back.
        outx = _convertback(xisfloat, xislist, xistuple, inx)
        outy = _convertback(yisfloat, yislist, xistuple, iny)
        return_data = (outx, outy)
        if inz is not None:
            return_data += (_convertback(zisfloat, zislist, zistuple, inz),)
        if intime is not None:
            return_data += (_convertback(tisfloat, tislist, tistuple, intime),)
        return return_data

    def itransform(
        self,
        points,
        switch=False,
        time_3rd=False,
        radians=False,
        errcheck=False,
        direction=TransformDirection.FORWARD,
    ):
        """
        Iterator/generator version of the function pyproj.Transformer.transform.


        Parameters
        ----------
        points: list
            List of point tuples.
        switch: boolean, optional
            If True x, y or lon,lat coordinates of points are switched to y, x
            or lat, lon. Default is False.
        time_3rd: boolean, optional
            If the input coordinates are 3 dimensional and the 3rd dimension is time.
        radians: boolean, optional
            If True, will expect input data to be in radians and will return radians
            if the projection is geographic. Default is False (degrees). Ignored for
            pipeline transformations.
        errcheck: boolean, optional (default False)
            If True an exception is raised if the transformation is invalid.
            By default errcheck=False and an invalid transformation
            returns ``inf`` and no exception is raised.
        direction: ~pyproj.enums.TransformDirection, optional
            The direction of the transform.
            Default is :attr:`~pyproj.enums.TransformDirection.FORWARD`.


        Example:

        >>> from pyproj import Transformer
        >>> transformer = Transformer.from_crs(4326, 2100)
        >>> points = [(22.95, 40.63), (22.81, 40.53), (23.51, 40.86)]
        >>> for pt in transformer.itransform(points): '{:.3f} {:.3f}'.format(*pt)
        '2221638.801 2637034.372'
        '2212924.125 2619851.898'
        '2238294.779 2703763.736'
        >>> pipeline_str = (
        ...     "+proj=pipeline +step +proj=longlat +ellps=WGS84 "
        ...     "+step +proj=unitconvert +xy_in=rad +xy_out=deg"
        ... )
        >>> pipe_trans = Transformer.from_pipeline(pipeline_str)
        >>> for pt in pipe_trans.itransform([(2.1, 0.001)]):
        ...     '{:.3f} {:.3f}'.format(*pt)
        '120.321 0.057'
        >>> transproj = Transformer.from_crs(
        ...     {"proj":'geocent', "ellps":'WGS84', "datum":'WGS84'},
        ...     "EPSG:4326",
        ...     always_xy=True,
        ... )
        >>> for pt in transproj.itransform(
        ...     [(-2704026.010, -4253051.810, 3895878.820)],
        ...     radians=True,
        ... ):
        ...     '{:.3f} {:.3f} {:.3f}'.format(*pt)
        '-2.137 0.661 -20.531'
        >>> transprojr = Transformer.from_crs(
        ...     "EPSG:4326",
        ...     {"proj":'geocent', "ellps":'WGS84', "datum":'WGS84'},
        ...     always_xy=True,
        ... )
        >>> for pt in transprojr.itransform(
        ...     [(-2.137, 0.661, -20.531)],
        ...     radians=True
        ... ):
        ...     '{:.3f} {:.3f} {:.3f}'.format(*pt)
        '-2704214.394 -4254414.478 3894270.731'
        >>> transproj_eq = Transformer.from_proj(
        ...     'EPSG:4326',
        ...     '+proj=longlat +datum=WGS84 +no_defs +type=crs',
        ...     always_xy=True,
        ...     skip_equivalent=True
        ... )
        >>> for pt in transproj_eq.itransform([(-2.137, 0.661)]):
        ...     '{:.3f} {:.3f}'.format(*pt)
        '-2.137 0.661'

        """
        it = iter(points)  # point iterator
        # get first point to check stride
        try:
            fst_pt = next(it)
        except StopIteration:
            raise ValueError("iterable must contain at least one point")

        stride = len(fst_pt)
        if stride not in (2, 3, 4):
            raise ValueError("points can contain up to 4 coordinates")

        if time_3rd and stride != 3:
            raise ValueError("'time_3rd' is only valid for 3 coordinates.")

        # create a coordinate sequence generator etc. x1,y1,z1,x2,y2,z2,....
        # chain so the generator returns the first point that was already acquired
        coord_gen = chain(fst_pt, (coords[c] for coords in it for c in range(stride)))

        while True:
            # create a temporary buffer storage for
            # the next 64 points (64*stride*8 bytes)
            buff = array("d", islice(coord_gen, 0, 64 * stride))
            if len(buff) == 0:
                break

            self._transformer._transform_sequence(
                stride,
                buff,
                switch=switch,
                direction=direction,
                time_3rd=time_3rd,
                radians=radians,
                errcheck=errcheck,
            )

            for pt in zip(*([iter(buff)] * stride)):
                yield pt

    def to_wkt(self, version=WktVersion.WKT2_2018, pretty=False):
        """
        Convert the projection to a WKT string.

        Version options:
          - WKT2_2015
          - WKT2_2015_SIMPLIFIED
          - WKT2_2018
          - WKT2_2018_SIMPLIFIED
          - WKT1_GDAL
          - WKT1_ESRI


        Parameters
        ----------
        version: ~pyproj.enums.WktVersion
            The version of the WKT output.
            Default is :attr:`~pyproj.enums.WktVersion.WKT2_2018`.
        pretty: bool
            If True, it will set the output to be a multiline string. Defaults to False.

        Returns
        -------
        str: The WKT string.
        """
        return self._transformer.to_wkt(version=version, pretty=pretty)

    def __str__(self):
        return self.definition

    def __repr__(self):
        return ("<{type_name}: {name}>\n" "{description}").format(
            type_name=self._transformer.type_name,
            name=self.name,
            description=self.description,
        )

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
            "features": geojson['features'],
            "grid_hash": gridHash}

    sendToCityIO(data, endpoint, token)


def makeGeoJSON(gridData, cityio):
    resultjson = "{\"type\": \"FeatureCollection\",\"features\": [" # geojson front matter

    # append features for all grid cells
    resultjson += appendPolyFeatures(gridData, cityio)

    resultjson += "]}" # geojson end matter
    return resultjson

def appendPolyFeatures(gridData, cityio):
    filledGrid = list(gridData)
    resultjson = ""

    proj = Transformer.from_crs(getFromCfg("compute_crs"), getFromCfg("output_crs"))
    for idx in range(len(filledGrid)):
        x = idx % cityio.ncols
        y = idx // cityio.ncols

        properties = {}

        pointlist = []

        fromPoint = cityio.Local2Geo(x,y) # upper left
        fromPoint = proj.transform(fromPoint[0],fromPoint[1])
        pointlist.append(fromPoint)

        toPoint = cityio.Local2Geo(x+1,y) # upper right
        toPoint = proj.transform(toPoint[0],toPoint[1])
        pointlist.append(toPoint)
        toPoint = cityio.Local2Geo(x+1,y+1) # bottom right
        toPoint = proj.transform(toPoint[0],toPoint[1])
        pointlist.append(toPoint)
        toPoint = cityio.Local2Geo(x,y+1) # bottom left
        toPoint = proj.transform(toPoint[0],toPoint[1])
        pointlist.append(toPoint)

        resultjson += PolyToGeoJSON(pointlist, idx, properties) # append feature, closes loop
        resultjson +=","

    resultjson = resultjson[:-1] # trim trailing comma
    return resultjson


def PolyToGeoJSON(points, id, properties):
    ret = "{\"type\": \"Feature\",\"id\": \""
    ret += str(id)
    ret += "\",\"geometry\": {\"type\": \"Polygon\",\"coordinates\": [["

    # lat,lon order
    for p in points:
        ret+="["+str(p[1])+","+str(p[0])+"],"
    ret+="["+str(points[0][1])+","+str(points[0][0])+"]" # closed ring, last one without trailing comma

    ret += "]]},"
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

    try:
        with open("token.txt") as f:
            token = f.readline()
        if token == "": token = None  # happens with empty file
    except IOError:
        token = None

    oldHash = ""

    while True:
        gridHash = getCurrentState("meta/hashes/grid", int(args.endpoint), token)
        if gridHash != {} and gridHash != oldHash:
            run(int(args.endpoint), token)
            oldHash = gridHash
        else:
            print("waiting for grid change")
            time.sleep(5)
