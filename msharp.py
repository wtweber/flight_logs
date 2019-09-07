import tabula
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter
import math
import pytz
import numpy as np

from CNAFenums import position, tz_enum, ldg_enum, app_enum, hours_enum
from local_func import process_ldg, process_app, julian, split_fp, process_pax_cargo, T_R_clean, match_lines

##################################################
##                                              ##
##             VARIABLE DEFINITIONS             ##
##                                              ##
##################################################

personal_info = {"id":"xxxxx1066", "name":"Weber"}

#filename = "two page.pdf"
filename = "Binder1.pdf"
#filename = "single navflr.pdf"

Type_filter = ['Aircraft']
TMS_filter = ['KC-130J']

msharp_data_raw = pd.read_excel('MSHARP2.0 AirCrewLogBook.xlsx', index_col=None)
Column_type = msharp_data_raw.iloc[2]

Landings_start = 0
App_start = 0
TR_start = 0

for i in range(0, len(Column_type)):
    if Column_type[i] == "Landings":
        Landings_start = i
    elif Column_type[i] == "App":
        App_start = i
    elif Column_type[i] == "T&R":
        TR_start = i

msharp_data_raw.iat[3,0] = "Date"
header = msharp_data_raw.iloc[3]
msharp_data = msharp_data_raw[5:]
msharp_data.columns = header

filtered_msharp = msharp_data[(msharp_data.TMS.isin(TMS_filter)) & (msharp_data.Type.isin(Type_filter))].reset_index(drop=True)

landing_pd = filtered_msharp.iloc[:, Landings_start:App_start]
app_pd = filtered_msharp.iloc[:, App_start:TR_start]
hour_pd = filtered_msharp.iloc[:, 0:Landings_start].fillna(0.0)

msharp_pd = pd.DataFrame(hour_pd)

landing_pd.fillna(0, inplace=True)
app_pd.fillna(0, inplace=True)

landing_pd = landing_pd.astype(int)
app_pd = app_pd.astype(int)

landings_title = {}
for title in landing_pd.columns:
    landing_pd.rename(columns={title:ldg_enum(str(title)[0]).name}, inplace=True)

for title in app_pd.columns:
    app_pd.rename(columns={title:app_enum(str(title)[0]).name}, inplace=True)

msharp_pd = msharp_pd.join(landing_pd)
msharp_pd = msharp_pd.join(app_pd)

(T_R_Lists, new_code) = T_R_clean(filtered_msharp.filter(like='T&R', axis=1))

msharp_pd["T&R"] = T_R_Lists
msharp_pd["new_code"] = new_code

msharp_pd["Dual Rcv"] = msharp_pd.apply(lambda row: row["TPT"] if row["new_code"] else 0.0, axis=1)



#print(filtered_msharp
logbook = []
record = []
process_ldg()

##################################################
##                                              ##
##                 PROGRAM START                ##
##                                              ##
##################################################

pdf_data = tabula.read_pdf(filename, multiple_tables=True, pages='all')

print("~~~~~~~~~~~~~~~~~~~")
for items in pdf_data:
    record.append(items)
    eval = items.isin(["A/C OR MSN CMDR SIGNATURE/GRADE"])
    if eval.any(axis=None):
        logbook.append(record)
        record = []

print("Read %i NAVFLIRs." % len(logbook))
print("~~~~~~~~~~~~~~~~~~~")

you_count = 0
TPT = 0.0

navflir_data = pd.DataFrame([])

for navflir in logbook:

    personal_dict = {}

    raw_aircraft_data = navflir[0]
    header = raw_aircraft_data.iloc[0]
    aircraft_data = raw_aircraft_data[1:]
    aircraft_data.columns = header

    personal_dict.update({"Flight #": aircraft_data["AIRLIFT"][1], "Buno": aircraft_data["BUNO"][1], "Side": aircraft_data["SIDE"][1]})

    crew_data = navflir[2]
    crew_data.columns = ['line', 'exc code', 'initial', 'name', 'id', 'crew position', 'cvc', 'fpt', 'cpt', 'sct', 'act', 'sim', 'night', 'l1', 'l2', 'l3', 'l4', 'a1', 'a2', 'a3', 'a4', 'tc1', 'tc2', 'tc3']

    crew_data.fillna(0, inplace=True)


    crew = []

    for index, person in crew_data.iterrows():
        if person["id"] == personal_info["id"] and person["name"] == personal_info["name"]:
            you_count += 1
            ldg_dict = process_ldg([person['l1'], person['l2'], person['l3'], person['l4']])
            #print(ldg_dict)
            app_dict = process_app([person['a1'], person['a2'], person['a3'], person['a4']])
            #print(app_dict)
            TPT += float(person["fpt"]) + float(person["cpt"])
            personal_dict.update({"navflir_TPT": float(person["fpt"]) + float(person["cpt"])})
        crew.append({"position":position(person["crew position"]).name,"name":"%s. %s"%(person['initial'], person['name'])})



    raw_leg_data = navflir[3][4:]
    jul_str = raw_leg_data.iloc[0][4]
    tz_str = raw_leg_data.iloc[0][2]
    time_str = raw_leg_data.iloc[0][3]
    launch_datetime = julian(jul_str, time_str, tz_str)
    tz_str = "Z"
    #print(jul_str)

    flight_path = []
    sorties = 0
    load_dict = {'cargo': 0, 'pax': 0}

    for i in range(0, len(raw_leg_data.index)):

        mod = i % 2

        if pd.isnull(raw_leg_data.iloc[i][3-mod]):
            jul_str = raw_leg_data.iloc[i][4]
            time_str = raw_leg_data.iloc[i][3]
            icao = raw_leg_data.iloc[i][5]
        else:
            jul_str = raw_leg_data.iloc[i][4-mod]
            time_str = raw_leg_data.iloc[i][3-mod]
            icao = raw_leg_data.iloc[i][5-mod]

        if not(mod):
            sorties += 1
            tz_str = raw_leg_data.iloc[i][2]
            flight_path.append(icao)
            leg_load = process_pax_cargo(list(map(int, raw_leg_data.iloc[i][11:19].fillna(0).tolist())))
            load_dict = Counter(leg_load) + Counter(load_dict)


        py_time = julian(jul_str, time_str, tz_str)
    flight_path.append(icao)
    route_data = split_fp(flight_path)
    personal_dict.update({"Sorties":sorties})
    personal_dict.update(route_data)
    personal_dict.update(load_dict)
    personal_dict.update({"LocalDate": launch_datetime.date(), "LocalTime": launch_datetime.time(), "UTCDate": launch_datetime.astimezone(pytz.utc).date(), "UTCTime": launch_datetime.astimezone(pytz.utc).time()})


    for items in navflir:
        eval = items.isin(["(REMARKS)"])
        if eval.any(axis=None):
            personal_dict.update({"Remarks":str(items.fillna("").iloc[-1][0]).replace("\r"," ")})

    navflir_data = navflir_data.append(personal_dict, ignore_index=True).fillna("")

print("~~~~~~~~~~~~~~~~~~~~~~~")
print("Found you on %i NAVFLIRs." % you_count)
print("Total Time: {:.1f}".format(TPT))

output_data = match_lines(msharp_pd, navflir_data)
output_data.columns = output_data.columns.fillna('DROP')
output_data.drop(columns=['Date', 'Device', 'navflir_TPT', 'DROP', 'new_code'], inplace=True)

output_data['PIC'] = output_data['ACMDR']#.apply(lambda x:x if x>0.0 else 0.0)
output_data['SIC'] = output_data['TPT'] - output_data['PIC']
output_data['Overwater'] = output_data['T&R'].apply(lambda x:True if '216' in x else False)
print(output_data.dtypes)

writer = pd.ExcelWriter('msharp_navflirs.xlsx', engine = 'xlsxwriter')
output_data.to_excel(writer, index=False)
writer.save()

output_data.to_csv ('msharp_navflir.csv', index = None, header=True)
