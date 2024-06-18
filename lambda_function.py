import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import time
import math
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging

# Logging einrichten
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Definiere Schlüssel und Geheimnis für die Lufthansa API
client_id = 'key'
client_secret = 'key'

# Definiere die zu verfolgenden Flüge
flights = [
    {"flight_number": "LH866", "flight_nr": "DLH866", "scheduled_time": "08:00"},
    {"flight_number": "LH860", "flight_nr": "DLH3LJ", "scheduled_time": "10:20"},
    {"flight_number": "LH858", "flight_nr": "DLH2KW", "scheduled_time": "16:00"},
    {"flight_number": "LH864", "flight_nr": "DLH7JK", "scheduled_time": "21:50"},
]

# Definiere ADSBexchange API-Variablen
adsb_api_url_template = "https://adsbexchange-com1.p.rapidapi.com/v2/callsign/{}/"
adsb_key = "key"
adsb_host = 'adsbexchange-com1.p.rapidapi.com'

# MongoDB-Konfiguration
uri = "mongodb+srv://roman116f:key@flightsml.uki32j1.mongodb.net/?retryWrites=true&w=majority&appName=flightsML"
db_name = "flightsml"
collection_name = "flights_data"

# Flughafen Frankfurt (FRA / EDDF)
fra_lat = 50.0379
fra_lon = 8.5622

# Flughafen Oslo (OSL / ENGM)
osl_lat = 60.1939
osl_lon = 11.1004

# Geplante Entfernung (FRA nach OSL in km)
distance_planned = 1190.0

def to_unix_timestamp(date_str):
    if date_str == 'N/A':
        return None
    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
    return int(time.mktime(dt.timetuple()))

def to_datetime(unix_timestamp):
    try:
        if unix_timestamp is None:
            return '0'
        dt = datetime.utcfromtimestamp(unix_timestamp / 1000)
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    except (OSError, ValueError) as e:
        logger.error(f"Fehler beim Konvertieren des Unix-Timestamps: {e}")
        return '0'

def map_flight_status_code(status_code):
    mapping = {
        'NA': 0,
        'LD': 1,
        'DP': 2,
        'CD': 3,
        'RT': 4,
    }
    return mapping.get(status_code, -1)

def map_time_status_code(status_code):
    mapping = {
        'NO': 0,
        'NI': 1,
        'FE': 2,
        'OT': 3,
        'DL': 4,
    }
    return mapping.get(status_code, -1)

def replace_none_and_ground_with_zero(data):
    return {key: (0 if value in [None, 'ground', 'N/A'] else value) for key, value in data.items()}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def fetch_flight_status(flight_number, date):
    try:
        logger.info(f"Flugstatus für {flight_number} von der Lufthansa API abrufen")
        token_url = "https://api.lufthansa.com/v1/oauth/token"
        data = {
            'grant_type': 'client_credentials'
        }

        response = requests.post(token_url, data=data, auth=HTTPBasicAuth(client_id, client_secret))

        if response.status_code == 200:
            token = response.json()['access_token']
            logger.info("OAuth-Token erfolgreich abgerufen")
        else:
            logger.error(f"Fehler beim Abrufen des OAuth-Tokens: {response.status_code}")
            logger.error(response.json())
            return None

        url = f"https://api.lufthansa.com/v1/operations/flightstatus/{flight_number}/{date}"

        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            flight_data = response.json()
            logger.info("Flugdaten erfolgreich abgerufen")
            
            try:
                departure = flight_data['FlightStatusResource']['Flights']['Flight'][0]['Departure']
                arrival = flight_data['FlightStatusResource']['Flights']['Flight'][0]['Arrival']
                flight_status = flight_data['FlightStatusResource']['Flights']['Flight'][0]['FlightStatus']
            except KeyError as e:
                logger.error(f"KeyError: {e}")
                logger.error("Das Format der Flugdaten könnte sich geändert haben oder ist fehlerhaft.")
                logger.error(json.dumps(flight_data, indent=4))
                return None

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
        else:
            logger.error(f"Fehler beim Abrufen der Flugdaten: {response.status_code}")
            logger.error("Antwortinhalt:")
            logger.error(response.json())
            return None
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Abrufen des Flugstatus aufgetreten: {e}")
        return None

def fetch_aircraft_data(flight_nr):
    try:
        logger.info(f"Flugzeugdaten für {flight_nr} von der ADSBexchange API abrufen")
        headers = {
            "X-RapidAPI-Key": adsb_key,
            "X-RapidAPI-Host": adsb_host
        }

        adsb_api_url = adsb_api_url_template.format(flight_nr)
        response = requests.get(adsb_api_url, headers=headers)
        
        if response.status_code == 200:
            try:
                aircraft_data = response.json()
                logger.info("Flugzeugdaten erfolgreich abgerufen")
                
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
                        else:
                            return None
            except json.JSONDecodeError as e:
                logger.error(f"JSONDecodeError: {e}")
                return None

        logger.error(f"Fehler beim Abrufen der Flugzeugdaten: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist beim Abrufen der Flugzeugdaten aufgetreten: {e}")
        return None

def track_flight(flight):
    now = datetime.now()
    scheduled_time = flight["scheduled_time"]
    scheduled_datetime = datetime.strptime(f"{now.strftime('%Y-%m-%d')} {scheduled_time}", "%Y-%m-%d %H:%M")
    start_time = scheduled_datetime - timedelta(minutes=5)
    end_time = scheduled_datetime + timedelta(hours=2)

    if start_time <= now <= end_time:
        logger.info(f"Tracking für Flug {flight['flight_number']} ({flight['flight_nr']}) wird gestartet")
        date = datetime.today().strftime('%Y-%m-%d')
        flight_status_data = fetch_flight_status(flight["flight_number"], date)
        if flight_status_data and flight_status_data["actual_arrival_time_utc"] == '0':
            logger.info(f"Der Flug {flight['flight_number']} hat seine tatsächliche Ankunftszeit erreicht. Das Tracking wird gestoppt.")
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

            try:
                client = MongoClient(uri, server_api=ServerApi('1'))
                db = client[db_name]
                collection = db[collection_name]
                collection.insert_one(combined_data)
                logger.info(f"Daten für Flug {flight['flight_number']} erfolgreich in MongoDB gespeichert")
            except Exception as e:
                logger.error(f"Fehler beim Speichern der Daten für Flug {flight['flight_number']} in MongoDB: {e}")

def lambda_handler(event, context):
    logger.info("AWS Lambda Funktion wurde gestartet")
    for flight in flights:
        track_flight(flight)
    return {
        'statusCode': 200,
        'body': json.dumps('Flug-Tracking abgeschlossen')
    }
