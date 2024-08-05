# Frontend is streamlitapp

import streamlit as st
import pandas as pd
import numpy as np
from pymongo import MongoClient
import datetime
import time
import folium
from streamlit_folium import st_folium
import pytz
from folium import features
import threading
import locale

# Lokalisierung auf Deutsch setzen
locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')

# MongoDB-Konfiguration
uri = "mongodb+srv://roman116f:key@flightsml.uki32j1.mongodb.net/?retryWrites=true&w=majority&appName=flightsML"
db_name = "flightsml"
collection_name = "flights_data"

# Verbindung zu MongoDB herstellen
client = MongoClient(uri)
db = client[db_name]
collection = db[collection_name]

# Funktion zum Konvertieren von Unix-Zeitstempeln in CET/CEST Sommerzeit
def convert_timestamps(df, fields, now_field):
    cet = pytz.timezone('Europe/Berlin')
    for field in fields:
        if field != now_field:
            for unit in ['s', 'ms', 'us']:
                try:
                    df[field] = pd.to_datetime(df[field], unit=unit, errors='coerce').dt.tz_localize('UTC').dt.tz_convert(cet).dt.strftime('%d.%m.%Y %H:%M:%S')
                    df[field] = df[field].fillna('0')
                    break
                except (pd.errors.OutOfBoundsDatetime, OverflowError):
                    continue
        else:
            df[field] = pd.to_datetime(df[field], unit='ms', errors='coerce').dt.tz_localize('UTC').dt.tz_convert(cet).dt.strftime('%d.%m.%Y %H:%M:%S')
            df[field] = df[field].fillna('0')
    return df

# Funktion zum Abrufen von Daten aus MongoDB
def fetch_data():
    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]
    data = list(collection.find())
    client.close()
    
    # JSON-Daten in ein pandas DataFrame normalisieren
    df = pd.json_normalize(data)
    
    # Zeitstempel konvertieren
    timestamp_fields = [
        'scheduled_departure_time_utc', 'actual_departure_time_utc', 
        'actual_arrival_time_utc', 'scheduled_arrival_time_utc', 'now'
    ]
    
    df = convert_timestamps(df, timestamp_fields, 'now')
    return df

# Funktion zur Erstellung der Karte
def create_map(lat, lon, aircraft_data):
    m = folium.Map(location=[lat, lon], zoom_start=6)

    # Flugzeugsymbol hinzufügen
    icon_url = 'flugzeug.png'  # Stellen Sie sicher, dass das Symbol im Arbeitsverzeichnis vorhanden ist
    icon = features.CustomIcon(icon_url, icon_size=(30, 30))
    folium.Marker([lat, lon], icon=icon, tooltip="Current Location").add_to(m)

    # Streckeninformationen
    fra_lat, fra_lon = aircraft_data['fra_lat'], aircraft_data['fra_lon']
    osl_lat, osl_lon = aircraft_data['osl_lat'], aircraft_data['osl_lon']
    route = [[fra_lat, fra_lon], [osl_lat, osl_lon]]
    
    # Luftlinie (gestrichelt, schwarz)
    folium.PolyLine(route, color='black', weight=1, dash_array='5').add_to(m)

    # Zurückgelegte Strecke (grün, etwas dicker)
    traveled_route = [[fra_lat, fra_lon], [lat, lon]]
    folium.PolyLine(traveled_route, color='green', weight=3).add_to(m)

    return m

# Daten zunächst abrufen
df = fetch_data()

# Aktuelles Datum
current_date = datetime.datetime.now().strftime('%A, %d %B %Y')

# Lufthansa-Logo und Titel hinzufügen
st.markdown(
    """
    <style>
    .header-container {
        display: flex;
        align-items: center;
    }
    .header-logo {
        width: 100px;
        margin-right: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# HTML für den Header mit eingebettetem Bild
header_html = f"""
<br>
<br>
<div style="display: flex; align-items: center;">
    <h3>Lufthansa</h3>
    <h4>LH860</h4>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# Angenommen, dass die neuesten Flugdaten der aktuelle Flug sind
current_flight = df.iloc[-1]

# Funktion zur Formatierung der Zeitstempel, wenn sie nicht null sind
def format_time(timestamp):
    if timestamp and timestamp != "0" and timestamp != 0:
        return pd.to_datetime(timestamp, format='%d.%m.%Y %H:%M:%S', errors='coerce').strftime('%H:%M Uhr')
    return "0"

# Formatierte Abflug- und Ankunftszeiten
actual_departure_time = format_time(current_flight['actual_departure_time_utc'])
scheduled_departure_time = format_time(current_flight['scheduled_departure_time_utc'])
actual_arrival_time = format_time(current_flight['actual_arrival_time_utc'])
scheduled_arrival_time = format_time(current_flight['scheduled_arrival_time_utc'])

# Fluginformationen formatieren
flight_info = f"""
<div style="display: flex; justify-content: space-between; align-items: flex-start; text-align: left;">
    <div style="flex: 1;">
        <h5>Frankfurt (FRA / EDDF)</h5>
        <p>{current_date}<br>
        <b>{actual_departure_time} CEST</b><br>
        {f'Planmäßig {scheduled_departure_time}' if scheduled_departure_time != "0" else ''}
        </p>
    </div>
    <div style="text-align: center; flex: 1; margin-top: 14px;">
        <br><br>
        <h5>{f'GELANDET UM {actual_arrival_time}' if actual_arrival_time != "0" else ''}</h5>
    </div>
    <div style="flex: 1;">
        <h5>Oslo (OSL / ENGM)</h5>
        <p>{current_date}<br>
        <b>{actual_arrival_time} CEST</b><br>
        {f'Planmäßig {scheduled_arrival_time}' if scheduled_arrival_time != "0" else ''}
        </p>
    </div>
</div>
"""

# HTML-Inhalte einbetten
st.markdown(flight_info, unsafe_allow_html=True)

# Karte erstellen und anzeigen
current_lat = current_flight['lat']
current_lon = current_flight['lon']
aircraft_map = create_map(current_lat, current_lon, current_flight)

# Hinzufügen von benutzerdefiniertem CSS, um die Ränder zu entfernen
st.markdown(
    """
    <style>
    .stApp {
        margin: 0;
        padding: 0;
    }
    .main > div {
        padding: 0;
    }
    iframe {
        margin: 0;
        padding: 0;
        display: block;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st_folium(aircraft_map, width=700, height=375)  # Die Höhe der Karte um ein Viertel reduzieren

# Vergangene Flüge anzeigen
st.header("Vergangene Flugaktivitäten")
df_sorted = df.sort_values(by='actual_arrival_time_utc', ascending=False)  # Daten nach Ankunftszeit sortieren
st.dataframe(df_sorted[['scheduled_departure_time_utc', 'actual_departure_time_utc', 
                 'scheduled_arrival_time_utc', 'actual_arrival_time_utc', 
                 'flight', 'flight_status_code']])

# Funktion zur Aktualisierung der Daten jede Minute
def update_data():
    while True:
        new_df = fetch_data()
        df_sorted = new_df.sort_values(by='actual_arrival_time_utc', ascending=False)  # Daten nach Ankunftszeit sortieren
        st.dataframe(df_sorted[['scheduled_departure_time_utc', 'actual_departure_time_utc', 
                                'scheduled_arrival_time_utc', 'actual_arrival_time_utc', 
                                'flight', 'flight_status_code']])
        time.sleep(60)

# Start der Datenaktualisierung im Hintergrund
update_thread = threading.Thread(target=update_data, daemon=True)
update_thread.start()
