import streamlit as st
import locale

# Lokalisierung auf Deutsch setzen
locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')

st.set_page_config(page_title="Flug Tracking: FRA - OSL", layout="wide")

def show_overview():
    st.title("Flug Tracking: Frankfurt - Oslo")
    st.markdown("""
    Diese AWS Lambda-Funktion ruft in Echtzeit Flugdaten und Flugzeuginformationen ab und speichert sie in einer Cloud-Datenbank (MongoDB). 
    Aktuelle Flugdaten (Abflugzeit, Ankunftszeit, Flugstatus usw.) werden von der Lufthansa-API abgerufen.
    Die ADSBexchange-API liefert Live-Daten des Flugzeugs. Basierend auf den Positionen des Flughafens und des Flugzeugs sowie unter Anwendung der Haversine-Formel wird die aktuelle Position des Flugzeugs berechnet und die Flugroute dargestellt (siehe unten).
    """)
    # Daten zunächst abrufen
    df = fetch_data()

    # Aktuelles Datum
    current_date = datetime.datetime.now().strftime('%A, %d %B %Y')

    # Lufthansa-Logo und Titel hinzufügen
    #st.markdown(
    #    """
    #    <style>
    #    .header-container {
    #        display: flex;
    #        align-items: center;
    #    }
    #    .header-logo {
    #        width: 100px;
    #        margin-right: 20px;
    #    }
    #    </style>
    #    """,
    #    unsafe_allow_html=True,
    #)


    # HTML für den Header mit eingebettetem Bild
    header_html = f"""
    <div style="display: flex; align-items: center;">
        <h3>Lufthansa, LH860</h3>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


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
            margin: 0px;
            padding: 0px;
        }
        .main > div {
            padding: 80px;
        }
        iframe {
            margin: 0px;
            padding: 0px;
            display: block;
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

from PIL import Image

# Bild laden und Größe anpassen
image = Image.open('roman.png')
image = image.resize((200, 200))

st.sidebar.markdown("""
    <style>
    .sidebar .sidebar-content {
        margin-top: 0px;
        padding-top: 0px;
        padding-bottom: 0px;
    }
    .sidebar .sidebar-content img {
        margin-top: 0px;
        margin-bottom: 0px;
    }
    .data-scientist {
        font-size: 12px;
    }
    .center-text {
        text-align: center;
    }
    .links {
        margin-top: 10px;
        display: flex;
        justify-content: center;
        gap: 10px;
    }
    .links a {
        text-decoration: none;
        color: #0366d6;
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.sidebar.image(image, use_column_width=False)
    st.sidebar.markdown("""
    <div class="center-text">
    Roman Langolf<br>
    <span class="data-scientist">Data Scientist</span>
    <div class="links">
        <a href="https://www.linkedin.com/in/roman-langolf-b9a834218/" target="_blank">LinkedIn</a> <a href="https://github.com/Roman116f/flight_status" target="_blank">GitHub</a>
    </div>
    </div>
    """, unsafe_allow_html=True)
    menu = ["Übersicht", "Lufthansa API", "ADSBexchange API", "MongoDB", "Flugberechnung", "Fehlerbehandlung", "AWS Lambda"]
    choice = st.sidebar.radio("", menu)
    if choice == "Übersicht":
        show_overview()
    elif choice == "Lufthansa API":
        show_lufthansa_api()
    elif choice == "ADSBexchange API":
        show_adsb_api()
    elif choice == "MongoDB":
        show_mongodb()
    elif choice == "Flugberechnung":
        show_flight_calculation()
    elif choice == "Fehlerbehandlung":
        show_error_handling()
    elif choice == "AWS Lambda":
        show_lambda()
    #st.sidebar.image('flugzeug2.png', width=100)

def show_lufthansa_api():
    st.title("Lufthansa API")
    st.markdown("""
    Der Code verwendet die Lufthansa API, um Flugstatusinformationen 
    abzurufen. Dies geschieht durch den Abruf eines OAuth-Tokens und 
    anschließender Abfrage der Flugstatus-API.
    
    **Wichtige Funktionen:**
    - Abrufen des OAuth-Tokens
    - Abrufen des Flugstatus
    - Verarbeitung und Umwandlung der Zeitstempel
    """)
    st.subheader("Geplante Abflugzeit (UTC)")
    st.json({"scheduled_departure_time_utc": 1717654800})

    st.subheader("Tatsächliche Abflugzeit (UTC)")
    st.json({"actual_departure_time_utc": 1717656540})

    st.subheader("Tatsächliche Ankunftszeit (UTC)")
    st.json({"actual_arrival_time_utc": 0})

    st.subheader("Geplante Ankunftszeit (UTC)")
    st.json({"scheduled_arrival_time_utc": 1717662000})

    st.subheader("Abflugzeit Status Code")
    st.json({"departure_time_status_code": 4})

    st.subheader("Ankunftszeit Status Code")
    st.json({"arrival_time_status_code": 4})

    st.subheader("Flug Status Code")
    st.json({"flight_status_code": 2})

    st.subheader("Flug")
    st.json({"flight": "DLH3LJ"})

    lufthansa_code = '''
import json
import requests
from requests.auth import HTTPBasicAuth

# Definiere Schlüssel und Geheimnis für die Lufthansa API
client_id = 'geheim'
client_secret = 'geheim'

def to_unix_timestamp(date_str):
    if date_str == 'N/A':
        return None
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
    return int(time.mktime(dt.timetuple()))

def map_time_status_code(status_code):
    mapping = {
        'NO': 0,
        'NI': 1,
        'FE': 2,
        'OT': 3,
        'DL': 4,
    }
    return mapping.get(status_code, -1)

def map_flight_status_code(status_code):
    mapping = {
        'NA': 0,
        'LD': 1,
        'DP': 2,
        'CD': 3,
        'RT': 4,
    }
    return mapping.get(status_code, -1)

def replace_none_and_ground_with_zero(data):
    return {key: (0 if value in [None, 'ground', 'N/A'] else value) for key, value in data.items()}

def fetch_flight_status(flight_number, date):
    try:
        token_url = "https://api.lufthansa.com/v1/oauth/token"
        data = {
            'grant_type': 'client_credentials'
        }

        response = requests.post(token_url, data=data, auth=HTTPBasicAuth(client_id, client_secret))

        if response.status_code == 200:
            token = response.json()['access_token']

        url = f"https://api.lufthansa.com/v1/operations/flightstatus/{flight_number}/{date}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            flight_data = response.json()
            
            departure = flight_data['FlightStatusResource']['Flights']['Flight'][0]['Departure']
            arrival = flight_data['FlightStatusResource']['Flights']['Flight'][0]['Arrival']
            flight_status = flight_data['FlightStatusResource']['Flights']['Flight'][0]['FlightStatus']

            scheduled_departure_time_utc = to_unix_timestamp(departure['ScheduledTimeUTC']['DateTime'].replace("Z", ""))
            actual_departure_time_utc = to_unix_timestamp(departure.get('ActualTimeUTC', {}).get('DateTime', 'N/A').replace("Z", ""))
            actual_arrival_time_utc = to_unix_timestamp(arrival.get('ActualTimeUTC', {}).get('DateTime', 'N/A').replace("Z", ""))
            scheduled_arrival_time_utc = to_unix_timestamp(arrival['ScheduledTimeUTC']['DateTime'].replace("Z", ""))
            departure_time_status_code = map_time_status_code(departure['TimeStatus']['Code'])
            arrival_time_status_code = map_time_status_code(arrival['TimeStatus']['Code'])
            flight_status_code = map_flight_status_code(flight_status['Code'])

            flight_status_output = {
                "scheduled_departure_time_utc": scheduled_departure_time_utc,
                "actual_departure_time_utc": actual_departure_time_utc,
                "actual_arrival_time_utc": actual_arrival_time_utc,
                "scheduled_arrival_time_utc": scheduled_arrival_time_utc,
                "departure_time_status_code": departure_time_status_code,
                "arrival_time_status_code": arrival_time_status_code,
                "flight_status_code": flight_status_code,
            }

            flight_status_output = replace_none_and_ground_with_zero(flight_status_output)

            return flight_status_output
    except Exception as e:
        return None
    '''
    st.code(lufthansa_code, language='python')

def show_adsb_api():
    st.title("ADSBexchange API")
    st.markdown("""
    Die ADSBexchange API wird verwendet, um aktuelle Flugzeugdaten zu 
    erhalten, einschließlich der geografischen Position, Geschwindigkeit 
    und Höhe des Flugzeugs.

    **Wichtige Funktionen:**
    - Abrufen der Flugzeugdaten
    - Filtern der relevanten Daten
    - Verarbeitung und Umwandlung der Daten
    """)
    st.subheader("Jetzt")
    st.json({"now": {"$numberLong": "1717669759488"}})

    st.subheader("Barometrische Höhe")
    st.json({"alt_baro": 12825})

    st.subheader("Geometrische Höhe")
    st.json({"alt_geom": 12600})

    st.subheader("Bodengeschwindigkeit")
    st.json({"gs": 352.9})

    st.subheader("Indizierte Airspeed")
    st.json({"ias": 282})

    st.subheader("Wahre Airspeed")
    st.json({"tas": 334})

    st.subheader("Mach")
    st.json({"mach": 0.536})

    st.subheader("Windrichtung")
    st.json({"wd": 212})

    st.subheader("Windgeschwindigkeit")
    st.json({"ws": 19})

    st.subheader("Kurs")
    st.json({"track": 32.38})

    st.subheader("Barometrische Steigrate")
    st.json({"baro_rate": -2048})

    st.subheader("Geometrische Steigrate")
    st.json({"geom_rate": -2048})

    st.subheader("Breitengrad")
    st.json({"lat": 60.058066})

    st.subheader("Längengrad")
    st.json({"lon": 10.558254})

    st.subheader("Navigation Höhe MCP")
    st.json({"nav_altitude_mcp": 10016})

    st.subheader("Navigation Kurs")
    st.json({"nav_heading": 0})

    st.subheader("Zurückgelegte Entfernung")
    st.json({"distance_traveled": 1121.2916680870917})

    st.subheader("Erwartete Entfernung")
    st.json({"distance_expected": 33.611728503391426})

    st.subheader("Geplante Entfernung")
    st.json({"distance_planned": 1190})

    st.subheader("FRA Breitengrad")
    st.json({"fra_lat": 50.0379})

    st.subheader("FRA Längengrad")
    st.json({"fra_lon": 8.5622})

    st.subheader("OSL Breitengrad")
    st.json({"osl_lat": 60.1939})

    st.subheader("OSL Längengrad")
    st.json({"osl_lon": 11.1004})
    adsb_code = '''
import json
import requests

adsb_api_url_template = "https://adsbexchange-com1.p.rapidapi.com/v2/callsign/{}/"
adsb_key = "geheim"
adsb_host = 'adsbexchange-com1.p.rapidapi.com'

def replace_none_and_ground_with_zero(data):
    return {key: (0 if value in [None, 'ground', 'N/A'] else value) for key, value in data.items()}

def fetch_aircraft_data(flight_nr):
    try:
        headers = {
            "X-RapidAPI-Key": adsb_key,
            "X-RapidAPI-Host": adsb_host
        }

        adsb_api_url = adsb_api_url_template.format(flight_nr)
        response = requests.get(adsb_api_url, headers=headers)
        
        if response.status_code == 200:
            aircraft_data = response.json()
            
            if 'ac' in aircraft_data:
                flight_data = [ac for ac in aircraft_data['ac'] if ac.get('flight').strip() == flight_nr]
                
                if flight_data:
                    desired_fields = [
                        'flight', 'now', 'alt_baro', 'alt_geom', 'gs', 'ias', 'tas', 'mach', 
                        'wd', 'ws', 'track', 'baro_rate', 'geom_rate', 
                        'lat', 'lon', 'nav_altitude_mcp', 'nav_heading'
                    ]

                    result_data = []
                    for data in flight_data:
                        filtered_data = {field: data.get(field) for field in desired_fields}
                        now_timestamp = aircraft_data.get("now")
                        filtered_data["now"] = now_timestamp
                        result_data.append(filtered_data)

                    if result_data:
                        result_data[0] = replace_none_and_ground_with_zero(result_data[0])
                        return result_data[0]
    except Exception as e:
        return None
    '''
    st.code(adsb_code, language='python')

def show_mongodb():
    st.title("MongoDB")
    st.markdown("""
    Der Code verwendet MongoDB zur Speicherung der abgerufenen Daten. 
    Die Konfiguration erfolgt über die MongoDB-URI und die Daten werden 
    in einer definierten Sammlung gespeichert.

    **Wichtige Funktionen:**
    - Verbindung zur MongoDB herstellen
    - Daten in MongoDB speichern
    """)
    mongodb_code = '''
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://roman116f:geheim@flightsml.uki32j1.mongodb.net/?retryWrites=true&w=majority&appName=flightsML"
db_name = "flightsml"
collection_name = "flights_data"

def save_to_mongodb(data):
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client[db_name]
        collection = db[collection_name]
        collection.insert_one(data)
        return True
    except Exception as e:
        return False
    '''
    st.code(mongodb_code, language='python')

def show_flight_calculation():
    st.title("Flugberechnung")
    st.markdown("""
    Berechnungen werden durchgeführt, um die Entfernung zwischen den 
    Flughäfen und die zurückgelegte Strecke zu berechnen. Dies geschieht 
    mithilfe der Haversine-Formel.

    **Wichtige Funktionen:**
    - Berechnung der Haversine-Distanz
    - Verarbeitung der geografischen Daten
    """)
    flight_calculation_code = '''
import math

fra_lat = 50.0379
fra_lon = 8.5622
osl_lat = 60.1939
osl_lon = 11.1004
distance_planned = 1190.0

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
    '''
    st.code(flight_calculation_code, language='python')

def show_error_handling():
    st.title("Fehlerbehandlung")
    st.markdown("""
    Der Code enthält eine umfassende Fehlerbehandlung, um sicherzustellen, 
    dass bei Fehlern entsprechende Meldungen protokolliert werden.

    **Wichtige Funktionen:**
    - Logging-Konfiguration
    - Fehlerprotokollierung und -behandlung
    """)
    error_handling_code = '''
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def log_error(message):
    try:
        logger.error(message)
    except Exception as e:
        logger.error(f"Fehler beim Protokollieren: {e}")
    '''
    st.code(error_handling_code, language='python')

def show_lambda():
    st.title("AWS Lambda")
    st.markdown("""
    Der Code ist für die Ausführung in einer AWS Lambda-Funktion 
    konzipiert, die regelmäßig ausgelöst wird, um die Flugverfolgung 
    durchzuführen.

    **Wichtige Funktionen:**
    - Definition der Lambda-Handler-Funktion
    - Aufruf der Tracking-Funktion für jeden Flug
    """)
    lambda_code = '''
def track_flight(flight):
    now = datetime.now()
    scheduled_time = flight["scheduled_time"]
    scheduled_datetime = datetime.strptime(f"{now.strftime('%Y-%m-%d')} {scheduled_time}", "%Y-%m-%d %H:%M")
    start_time = scheduled_datetime - timedelta(minutes=5)
    end_time = scheduled_datetime + timedelta(hours=2)

    if start_time <= now <= end_time:
        date = datetime.today().strftime('%Y-%m-%d')
        flight_status_data = fetch_flight_status(flight["flight_number"], date)
        if flight_status_data and flight_status_data["actual_arrival_time_utc"] == '0':
            return

        aircraft_data = fetch_aircraft_data(flight["flight_nr"])

        if flight_status_data and aircraft_data:
            current_lat = aircraft_data['lat']
            current_lon = aircraft_data['lon']
            
            distance_traveled = haversine(fra_lat, fra_lon, current_lat, current_lon)
            distance_expected = haversine(current_lat, current_lon, osl_lat, osl_lon)

            combined_data = {
                **flight_status_data,
                **aircraft_data,
                "distance_traveled": distance_traveled,
                "distance_expected": distance_expected,
                "distance_planned": distance_planned,
                "fra_lat": fra_lat,
                "fra_lon": fra_lon,
                "osl_lat": osl_lat,
                "osl_lon": osl_lon
            }

            save_to_mongodb(combined_data)

def lambda_handler(event, context):
    for flight in flights:
        track_flight(flight)
    return {
        'statusCode': 200,
        'body': json.dumps('Flug-Tracking abgeschlossen')
    }
    '''
    st.code(lambda_code, language='python')

if __name__ == "__main__":
    main()
