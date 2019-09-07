import pandas as pd
from datetime import datetime, timedelta
from collections import Counter
import math
import pytz
import numpy as np
from CNAFenums import position, tz_enum, ldg_enum, app_enum, hours_enum

##################################################
##                                              ##
##             FUNCTION DEFINITIONS             ##
##                                              ##
##################################################

def process_ldg(ldg_data = []):
    ldg = {}
    for item in ldg_data:
        if item != 0:
            ldg.update({ldg_enum(item[0]).name:int(item[1:len(item)])})
    return(ldg)

def process_app(app_data = []):
    app = {}
    for item in app_data:
        if item != 0:
            app.update({app_enum(item[0]).name:int(item[1:len(item)])})
    return(app)


def julian(jul_str, time_str = '0000', tz = 'Z'):
    jul = int(jul_str)
    time = int(time_str)
    year = jul//1000
    days = (jul%1000)-1
    hours = (time//100) #+ tz_enum[tz].value
    min = time%100

    time_zone = pytz.timezone(tz_enum[tz].value)

    if hours < 0:
        days -= 1
        hours += 24
    elif hours > 23:
        days += 1
        hours -= 24

    if tz == 'Z':
        print('Imported a Zulu time')

    flight_date = time_zone.localize(datetime(2000+year, 1, 1, hours, min, 0) + timedelta(days=days))
    return flight_date

def split_fp(flight_path = ['ZZZZ', 'ZZZZ']):
    if len(flight_path) == 2:
        return {'From':flight_path[0], 'To':flight_path[-1], 'Route':''}
    else:
        seperator = ", "
        route_str = seperator.join(flight_path[1:len(flight_path)-1])
        #for i in range(1, flight_path.len()-1):
        return {'From':flight_path[0], 'To':flight_path[-1], 'Route':route_str}

def process_pax_cargo(load = [0, 0, 0, 0, 0, 0, 0, 0]):
    pax = sum(load[0:5], load[6])
    cargo = load[5] + load[7]
    return({'pax':pax, 'cargo':cargo})

def T_R_clean(tr = pd.DataFrame([])):
    recieved_codes = []
    tr_strings = []
    initial_codes = []
    seperator = ", "
    #print(tr[0:])
    for flight in tr.itertuples():
        tr_list = []
        new_code = False
        #print(flight)
        for code in flight:
            #print(type(code))
            if not math.isnan(code) and code > 1000:
                tr_list.append(str(code))
                if code not in recieved_codes:
                    new_code = True
                    recieved_codes.append(code)
        tr_strings.append(seperator.join(tr_list))
        initial_codes.append(new_code)
    return(tr_strings, initial_codes)

def match_lines(m, n):
    output_pd = pd.DataFrame([],columns=m.columns.tolist() + n.columns.tolist())
    #m = m.reindex(columns = m.columns.tolist() + n.columns.tolist())
    for index, record in n.iterrows():
        #print(record)
        f_date = pd.Timestamp(record.LocalDate)
        f_buno = record.Buno
        f_tpt = record.navflir_TPT
        index_1 = m.index[m["Date"] == f_date]
        index_2 = m.index[m["Device"] == f_buno]
        index_3 = m.index[np.isclose(m["TPT"], f_tpt, atol=0.001)]
        index = list(set(index_1).intersection(index_2, index_3))
        if not len(index):
            print("Didnt find a match for line %i" % index)
        elif len(index)>1:
            print("Found muultiple matches to line: %i" % index)
        else:
            matched_line = pd.concat([m.iloc[index[0]], record], axis=0)
            output_pd = output_pd.append(matched_line, ignore_index=True)
        #print(index_3)
    return(output_pd)
