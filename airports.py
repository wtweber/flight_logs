import json
import requests

ICAO_API_KEY = "41665130-d5a7-11e9-9e95-755433902422"

class airport():
    def __init__(self):
        self.latitude = 0.0
        self.longitude = 0.0
        self.proc_runways = 0
        self.airportCode = ""
        self.airportName = ""
        self.countryCode = ""
        self.FIRcode = ""
        self.FIRname = ""
        self.region = ""
        self.elevation = 0
        self.is_international = False
        self.iatacode = ""
        self.countryName = ""

    def fromDICT(self, obj):
        self.__dict__ = obj
        return self

    def GeoJSON(self):
        geo = {"type": "Feature","geometry": {"type":"Point"}}
        geo["geometry"]["coordinates"] = [self.longitude, self.latitude]
        geo["properties"] = {"ICAO": self.airportCode}
        geo["properties"]["name"] =  self.airportName
        return json.dumps(geo)

def getAirport(ICAO = None):
    if ICAO:
        params = {"api_key": ICAO_API_KEY, "airports": ICAO}
        response = requests.get("https://v4p4sz5ijk.execute-api.us-east-1.amazonaws.com/anbdata/airports/locations/operational-list", params = params)
        response_dict = json.loads(response.text)
        for object in response_dict:
            #air = airport()
            return airport().fromDICT(object)
    return airport()


# airfield = getAirport(ICAO = "KNGP")
# print(airfield.airportName.capitalize())
# print(airfield.GeoJSON())
