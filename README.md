# flights_predict

English:
This AWS Lambda function retrieves flight data and aircraft information in real time and stores it in a cloud database (MongoDB). Current flight data (departure time, arrival time, flight status, etc.) is retrieved from the Lufthansa API. The ADSBexchange API provides live data from the aircraft. Based on the positions of the airport and the aircraft and using the Haversine formula, the current position of the aircraft is calculated and the flight route is displayed (see below).

German:
Diese AWS Lambda-Funktion ruft in Echtzeit Flugdaten und Flugzeuginformationen ab und speichert sie in einer Cloud-Datenbank (MongoDB). Aktuelle Flugdaten (Abflugzeit, Ankunftszeit, Flugstatus usw.) werden von der Lufthansa-API abgerufen. Die ADSBexchange-API liefert Live-Daten des Flugzeugs. Basierend auf den Positionen des Flughafens und des Flugzeugs sowie unter Anwendung der Haversine-Formel wird die aktuelle Position des Flugzeugs berechnet und die Flugroute dargestellt (siehe unten).

![streamlitapp](https://github.com/Roman116f/flights_predict/assets/161879590/bd001134-a0b4-4a2e-9cc9-928419adb892)
