import uuid
from datetime import datetime, date, time
from CNAFenums import Role, Approach, Landing
import json
from enum import Enum, auto
from airports import airport, getAirport
#class time(dict)
dataV = "data"
datetime_str = '%Y-%m-%dT%H:%M:%S.%f'

class aircraft():
    def __init__(self):
        self.buno = ""


class hours():
    def __init__(self, fpt=0.0, cpt=0.0, sct=0.0, AIT = 0.0, SIT = 0.0):
        self.fpt = fpt
        self.cpt = cpt
        self.sct = sct
        self.AIT = AIT
        self.SIT = SIT

    def toDict(self):
        d = {"_type": "hours_class"}
        d[dataV] = self.__dict__
        return d

    def fromDict(self, obj):
        self.__dict__ = obj

    def TFT(self):
        return self.fpt + self.cpt + self.sct

    def TPT(self):
        return self.fpt + self.cpt

    def Inst(self):
        return self.AIT + self.SIT

class leg():
    def __init__(self, origin = airport(), to_time = datetime.now(), destination = airport(), land_time = datetime.now()):
        self.origin = origin
        self.destination = destination

        if isinstance(to_time, datetime):
            self.take_off = to_time
        elif isinstance(to_time, str):
            self.take_off = datetime.strptime(launch_time, datetime_str)
        else:
            self.take_off = datetime.now()

        if isinstance(land_time, datetime):
            self.land = land_time
        elif isinstance(to_time, str):
            self.land = datetime.strptime(land_time, datetime_str)
        else:
            self.land = datetime.now()

    def toDict(self):
        d = {"_type": "leg_class"}
        d[dataV] = self.__dict__
        return d

    def fromDict(self, obj):
        self.__dict__ = obj
        if isinstance(self.take_off, str):
            self.take_off = datetime.strptime(self.take_off, datetime_str)
        if isinstance(self.land, str):
            self.land = datetime.strptime(self.land, datetime_str)
        return self

    def __lt__(self, other):
        return self.take_off > other.take_off

class app():
    def __init__(self, type = Approach.OTHER, number = 0):
        self.type = type
        self.count = number

    def toDict(self):
        d = {"type": {"_type":"app_enum", dataV:str(self.type.value)}, "count":self.count}
        return d

    def fromDict(self, obj):
        self.count = obj["count"]
        self.type = Approach(obj["type"][dataV])
        return self

class ldg():
    def __init__(self, type = Landing.OTHER, number = 0):
        self.type = type
        self.count = number

    def toDict(self):
        d = {"type": {"_type":"ldg_enum", dataV:str(self.type.value)}, "count":self.count}
        return d

    def fromDict(self, obj):
        self.count = obj["count"]
        self.type = Landing(obj["type"][dataV])
        return self

class flight():
    def __init__(self, record = uuid.uuid4(), legs = [], flight_hours= hours(), role = Role.OTHER, approaches = [], landings = []):
        self.record = str(record)
        self.legs = legs
        self.flight_hours = flight_hours
        self.role = role
        self.approaches = approaches
        self.landings = landings

    def toJSON(self):
        return json.dumps(self, cls=FlightEncoder, sort_keys=True, indent=4)
        #return json.dumps(self, sort_keys=True, indent=4, default=lambda o: o.__dict__)

    def add_leg(self, leg):
        self.legs = self.legs + [leg]
        self.legs.sort()

    def add_App(self, app):
        index = -1
        for i, approach in enumerate(self.approaches):
            if app.type == approach.type:
                index = i
        if index == -1:
            self.approaches = self.approaches + [app]
        else:
            self.approaches[index].count += 1

    def add_Ldg(self, ldg):
        index = -1
        for i, landing in enumerate(self.landings):
            if ldg.type == landing.type:
                index = i
        if index == -1:
            self.landings = self.landings + [ldg]
        else:
            self.landings[index].count += 1

    def origin(self):
        if len(self.legs) == 0:
            return None
        else:
            return self.legs[0].origin.airportCode

    def destination(self):
        if len(self.legs) == 0:
            return None
        else:
            return self.legs[-1].destination.airportCode
    def route_str(self):
        if len(self.legs) <= 1:
            return ""
        elif len(self.legs) == 2:
            return self.legs[0].destination.airportCode
        else:
            route_list = [self.legs[0].destination.airportCode]
            for index in range(1,len(self.legs)-1):
                route_list.append(self.legs[index].destination.airportCode)
            return "-".join(route_list)

    def route_geoJSON(self):
        if len(self.legs) == 0:
            return None
        geo = {"type": "Feature", "geometry": {"type":"LineString","coordinates": [[self.legs[0].origin.longitude, self.legs[0].origin.latitude]]}}
        for index in range(0,len(self.legs)):
            geo["geometry"]["coordinates"].append([self.legs[index].destination.longitude, self.legs[index].destination.latitude])
        geo["properties"] = {"name": self.record}
        geo["properties"]["route"] =  "%s-%s-%s"%(self.origin(), self.route_str(), self.destination())
        return json.dumps(geo)

    def PIC(self):
        if self.role in [Role.ACFT_CMDR, Role.AC_MSN_CMDR] or (self.role == Role.INSTRUCTOR and self.hours.fpt + self.flight_hours.cpt > 0):
            return self.flight_hours.TFT()
        else:
            return 0.0

    def SIC(self):
        if self.PIC():
            return self.flight_hours.TPT()
        else:
            return 0.0


PUBLIC_ENUMS = {
    'Role': Role,
    # ...
}

PUBLIC_CLASSES = {
    'leg': leg,
    'hours': hours
}

FLIGHT_CLASS = {
    'flight': flight
}



class FlightEncoder(json.JSONEncoder):
    def default(self, obj):
        #print(type(obj))
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif type(obj) in FLIGHT_CLASS.values():
            #print("FLIGHT JSON")
            val = {"record": obj.record}
            val["flight_hours"] = obj.flight_hours.toDict()
            val["legs"] = {"_type": "legs_list", dataV: []}
            for item in obj.legs:
                val["legs"][dataV].append(item.toDict())
            val["Role"] = {"_type":"role_enum", dataV:str(obj.role.value)}
            val["Approaches"] = {"_type": "app_list", dataV: []}
            for item in obj.approaches:
                val["Approaches"][dataV].append(item.toDict())
            val["Landings"] = {"_type": "ldg_list", dataV: []}
            for item in obj.landings:
                val["Landings"][dataV].append(item.toDict())
            return val
        elif isinstance(obj, airport):
            return obj.__dict__
        else:
            print(type(obj))
            return json.JSONEncoder.default(self, obj)
#print(str(datetime.now()))

def FlightJSONDecoder(json_data):
    tmp_flt = flight()
    obj = json.loads(json_data)
    for key, value in obj.items():
        if isinstance(value, dict):
            if value["_type"] == "role_enum":
                tmp_flt.role = Role(value[dataV])
            elif value["_type"] == "hours_class":
                tmp_flt.flight_hours.fromDict(value[dataV])
            elif value["_type"] == "legs_list":
                for item in value[dataV]:
                    tmp_leg = leg()
                    tmp_flt.add_leg(tmp_leg.fromDict(item[dataV]))
            elif value["_type"] == "app_list":
                for item in value[dataV]:
                    tmp_app = app()
                    tmp_flt.add_App(tmp_app.fromDict(item))
            elif value["_type"] == "ldg_list":
                for item in value[dataV]:
                    tmp_ldg = ldg()
                    tmp_flt.add_Ldg(tmp_ldg.fromDict(item))
        elif key == "record":
            tmp_flt.record = value
    return tmp_flt

record = str(uuid.uuid4())
test_flight = flight()
test_flight.add_leg(leg(origin=getAirport(ICAO = "ROTM"), destination=getAirport(ICAO = "RKPK")))
test_flight.add_leg(leg(origin=getAirport(ICAO = "RKPK"), destination=getAirport(ICAO = "RJOI")))
test_flight.add_leg(leg(origin=getAirport(ICAO = "RJOI"), destination=getAirport(ICAO = "PAED")))

#test_flight.add_leg(leg(origin="RKPK", destination="RJOI"))
#test_flight.add_leg(leg(origin="RJOI", destination='RKPK'))
#test_flight.add_leg(leg(origin="RKPK", destination="ROTM"))
test_flight.add_App(app())
test_flight.add_Ldg(ldg())
test_flight.role = Role('A')

json_data = test_flight.toJSON()
print(json_data)
print("~~~~~~~~~~~~~~~")
print(test_flight.route_geoJSON())

# loaded_flight = FlightJSONDecoder(json_data)
# record = str(uuid.uuid4())
# t_flight = flight()
# #print(t_flight.toJSON())
# print(loaded_flight.toJSON())
# print("%s/%s/%s"%(loaded_flight.origin(), loaded_flight.route(), loaded_flight.destination()))
