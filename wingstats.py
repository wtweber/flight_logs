import tabula
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import sys

from CNAFenums import role_enum, tz_enum, ldg_enum, app_enum, hours_enum
from local_func import process_ldg, process_app, julian, split_fp, process_pax_cargo, T_R_clean, match_lines

wingstats_strs = [".xls", "IndividualFlightHours"]


def main():
    flights = pd.DataFrame()
    for var in sys.argv[1:]:
        if all(x in var for x in wingstats_strs):
            flights = wingstats(var)
        if "navflir" in var:
            flights = tims_navflirs("C114PBA.pdf", flights)
    if "table" in sys.argv:
        #print(flights.dtypes)
        with pd.option_context('display.max_rows', None):
            print(flights)
    if "json" in sys.argv:
        print(flights.to_json(orient='table', index=False))

def wingstats(file):
        output_data = pd.DataFrame()
        wingstats_data_raw = pd.read_excel(file, index_col=None)
        wing_data = clean_wing_stats(wingstats_data_raw)
        #print(wing_data.dtypes)
        #with pd.option_context('display.max_rows', None):
        #    print(wing_data)
        for index, data in wing_data.iterrows():
            flight_date = datetime.strptime(data["Date"]+"CST", "%m/%d/%Y %H:%M%Z")
            #flight_dict = {"Date":flight_date.replace(tzinfo=pytz.timezone(tz_enum["Z"].value))}
            flight_dict = {"Date": flight_date.astimezone(pytz.utc)}
            if data["IPT"]>0:
                flight_dict.update({"PIC": data["TFT"]})
                flight_dict.update({"SIC": 0})
                flight_dict.update({"DualGiven": data["IPT"]})
                flight_dict.update({"Commander": data["TFT"]})
                flight_dict.update({"Role":"I"})
            else:
                flight_dict.update({"PIC": 0})
                flight_dict.update({"SIC": data["TPT"]})
                if flight_date < datetime(2012, 2, 10):
                    flight_dict.update({"Role":"M"})
                else:
                    flight_dict.update({"Role":"C"})

            flight_dict.update({"FPT": data["FPT"]})
            flight_dict.update({"CPT": data["CPT"]})
            flight_dict.update(clean_ldg((data["Lnds"])))
            flight_dict.update(clean_app((data["Apps"])))
            flight_dict.update({"Night": data["NT"]})
            flight_dict.update({"ActualInst": data["AIT"]})
            flight_dict.update({"SimInst": data["SIT"]})
            flight_dict.update({"NightVisGoggle": data["NVG"]})
            flight_dict.update({"SpecialCrew": data["SCT"]})
            flight_dict.update({"DocumentNumber": data["Document Number"]})
            flight_dict.update({"TMR": data["Mission Code"]})
            flight_dict.update({"Sorties": data["# Sorties"]})
            flight_dict.update({"Event": data["Event"]})
            flight_dict.update({"Comments": data["Remarks"]})
            flight_dict.update({"Buno": str(data["Bureau #"])})
            flight_dict.update({"Side": str(data["Side #"])})
            flight_dict.update({"Type": data["Model"]})

            output_data = output_data.append(flight_dict, ignore_index=True)

            output_data.fillna({"Comments":"", "Event":""}, inplace=True)
            output_data.fillna(0, inplace=True)

        return output_data

def tims_navflirs(folder, flights=pd.DataFrame()):

    pdf_data = tabula.read_pdf(folder, multiple_tables=True, pages='all', lattice = True, silent = True)

    raw_navflr = pdf_data[0]

    admin_index = raw_navflr.index[raw_navflr.loc[:, 0]=='Admin'].tolist()[0]
    sorties_index = raw_navflr.index[raw_navflr.loc[:, 0] == 'Sorties'].tolist()[0]
    logistics_index = raw_navflr.index[raw_navflr.loc[:, 0] == 'Logistics'].tolist()[0]
    aircrew_index = raw_navflr.index[raw_navflr.loc[:, 0] == 'Aircrew'].tolist()[0]
    tactical_index = raw_navflr.index[raw_navflr.loc[:, 0] == 'Tactical'].tolist()[0]
    training_index = raw_navflr.index[raw_navflr.loc[:, 0] == 'Training'].tolist()[0]
    activities_index = raw_navflr.index[raw_navflr.loc[:, 0] == 'Activities'].tolist()[0]
    engine_index = raw_navflr.index[raw_navflr.loc[:, 0] == 'Engines'].tolist()[0]

    #temp_pd.dropna(axis=1, how='all', inplace=True)
    #temp_pd.dropna(axis=0, how='all', inplace=True)
    Admin = clean_pd(raw_navflr.loc[admin_index+1:sorties_index-1, :])
    Sorties = clean_pd(raw_navflr.loc[sorties_index+1:logistics_index-1, :])
    Aircrew = clean_pd(raw_navflr.loc[aircrew_index+1:tactical_index-1, :])
    Activities = clean_pd(raw_navflr.loc[activities_index+1:engine_index-1, :])
    Training = clean_pd(raw_navflr.loc[training_index+1:activities_index-1, :])

    flights["TR"] = np.nan
    flights["TR"] = flights["TR"].astype('object')

    #flights.fillna(value={"TR":[]}, inplace=True)
    #print(Training)
    me = Aircrew.loc[Aircrew.loc[:, 'EDIPI'] == 'xxxxxx6264', :]
    #print(Admin.at[1, 'Document'])
    matched_index = flights.loc[flights['DocumentNumber'] == Admin.at[1, 'Document']].index.values
    if len(matched_index) == 1:
        flights.at[matched_index[0], "Role"] = me["Role"].values[0]
        stops = []
        for index, leg in Sorties.iterrows():
            if index == 1:
                stops.append(leg["Departure ICAO"])
            stops.append(leg["Arrival ICAO"])
        flights.at[matched_index[0], "Origin"] = stops[0]
        flights.at[matched_index[0], "Destination"] = stops[-1]

        if len(stops) > 2:
            flights.at[matched_index[0], "Route"] = stops[1:-1]

        #print(Training.index[Training.iloc[:, 3]=='xxxxxx6264'].tolist())

        #me_training = Training.loc[Training.loc[:, 'SSN/EDIPI'] == 'xxxxxx6264', :]
        T_R = []
        others = []
        for index, line in Training.iterrows():
            print()
            if line.loc["SSN/EDIPI"].values[0] == "xxxxxx6264":
                if line["Event"] != "None":
                    T_R.append(line["Event"])
            else:
                others.append("%s for %s"%( line["Event"], line["Person Receiving Event"]))
        flights.at[matched_index[0], "TR"] = T_R
        print(flights.dtypes)
    elif len(matched_index) > 1:
        print("ERROR FOUND MULTIPLE MATCHING RECORDS: %s"%Admin.at[1, 'Document'])
    else:
        print("NO MATCH FOUND.")

    return flights

def clean_wing_stats(wingstats):
    clipped_data = wingstats.iloc[5:]
    clipped_data.columns = wingstats.iloc[4]
    #clipped_data.columns[0]='Index'
    clipped_data.drop(clipped_data.loc[clipped_data["Date"]=="Date"].index, inplace=True)
    clipped_data.drop(clipped_data.loc[clipped_data["Date"]=="Period Totals:"].index, inplace=True)
    clipped_data.dropna(how='all', inplace=True)
    clipped_data.reset_index(drop=True, inplace=True)
    #print(column_names)
    for index, data in clipped_data[::-1].iterrows():
        if pd.isnull(data['Date']):
            if not pd.isnull(data['Event']):
                #print(data['Event'])
                clipped_data.iloc[index-1]['Event'] = clipped_data.iloc[index-1]['Event'] + "/" + data['Event']
            if not pd.isnull(data['Remarks']):
                clipped_data.iloc[index-1]['Remarks'] = clipped_data.iloc[index-1]['Remarks'] + "/" + data['Remarks']
    clipped_data.dropna(subset=['Date'], inplace=True)
    clipped_data.reset_index(drop=True, inplace=True)

    return(clipped_data)

def clean_ldg(ldg_str):
    if pd.isnull(ldg_str):
        return {}
    else:
        ldg_dict = {}
    val = str(ldg_str).split()
    for i in val:
        parts = i.split('/')
        if len(parts)==2:
            ldg_dict.update({ldg_enum(parts[0]).name:int(parts[1])})
    return ldg_dict

def clean_app(app_str):
    if pd.isnull(app_str):
        return {}
    else:
        app_dict = {}
    val = str(app_str).split()
    for i in val:
        parts = i.split('/')
        if len(parts)==2:
            app_dict.update({app_enum(parts[0]).name:int(parts[1])})
    return app_dict

def format_date(date_str):
    return 0

def clean_pd(panda):

    panda.dropna(axis=1, how='all', inplace=True)
    panda.dropna(axis=0, how='all', inplace=True)
    panda.reset_index(drop=True, inplace=True)
    panda.columns = panda.iloc[0]
    panda.drop(panda.index[0], inplace=True)

    return panda

if __name__ == "__main__":
    main()
