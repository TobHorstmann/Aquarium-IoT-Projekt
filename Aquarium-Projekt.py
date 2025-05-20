# Ersteller: Tobias Horstmann
# Datum: 04.03.2025
# Programm "Aquariumüberwachung"

#############################################################################################

# Libaries
import network
import json
import ds18x20
import onewire
import machine
import time
from machine import Pin,time_pulse_us 
from time import sleep
from umqtt.simple import MQTTClient
from hcsr04 import HCSR04

#############################################################################################

#Globale Konfiguration

# Pin, an dem der DS18B20 angeschlossen ist
data_pin = machine.Pin(40) 

# Initialisierung OneWire und DS18B20
ow = onewire.OneWire(machine.Pin(data_pin))
ds = ds18x20.DS18X20(ow)
roms = ds.scan()

# Pins für HC-SR04 definieren
TRIG_PIN = 12  							# TRIG_Pin wird am GPIO12 angeschlossen
ECHO_PIN = 13 							# ECHO_Pin wird am GPIO13 angeschlossen
trig = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

# Pin für das Relais definieren						
relais = Pin(5, Pin.OUT)
relais.value(0)							# Relais aus (Pumpe aus)

# Schwellenwert in Zentimeter
min_abstand = 2.275  					# Abstand zur Wasseroberfläche (anpassbar!)

#############################################################################################

# WLAN-Zugangsdaten
SSID = "XXX"
PASSWORD = "XXX"

#############################################################################################

# MQTT-Broker Details
BROKER = "192.168.178.66"  	# IP vom Broker
PORT = 1883                 # Port für MQTT
TOPIC_PUB = "Aquarium/Sensorwerte" # Topic, an das Daten gesendet werden
CLIENT_ID = "ESP_32"   		# Eindeutige Client-ID

#############################################################################################

# Funktion: Verbindung zum WLAN herstellen

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
print("Verbindung zum WLAN wird hergestellt...")
while not wlan.isconnected():
    time.sleep(1)
print("WLAN verbunden:", wlan.ifconfig())

#############################################################################################

# MQTT-Client erzeugen, Callback festlegen und Topic abonnieren
client = MQTTClient(CLIENT_ID, BROKER, PORT)
sleep(1)
client.connect()
print(f"Verbunden mit MQTT-Broker: {BROKER}")   


#############################################################################################

#Funktion für die Sensorik

def messung_distanz_cm():
    # Ultraschallimpuls senden
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    # Echo-Zeit messen
    dauer = time_pulse_us(echo, 1, 30000)  # Timeout nach 30ms (max ca. 5m Entfernung)

    # Entfernung berechnen (Schallgeschwindigkeit ca. 343 m/s)
    distanz_cm = (dauer / 2) * 0.0343
    return distanz_cm
                                        
def messung_temperatur():				#Funktion für die Messung der Temperatur
    ds.convert_temp()					#Umwandlung in Temperatur
    time.sleep_ms(750)					#Zeit für Umwandlung
    temp = ds.read_temp(roms[0])		#Auslesen der Temperatur
    return temp

#############################################################################################

# Hauptprogramm

while True:
        
    abstand = messung_distanz_cm()									#Messwert wird variable zugeschwiesen
    print("Gemessener Abstand:", round(abstand, 2), "cm")			#Messwert wird in der Konsole ausgegeben
    
    temperatur = messung_temperatur()								#Messwert wird variable zugeschwiesen
    print ("Gemessene Temperatur:", round(temperatur, 2),"Celsius")	#Messwert wird in der Konsole ausgegeben

    fuellstand = 13-abstand					#Berrechnung des Aktuellenfüllstands, 12.5cm vom Sensor zum Boden
            
    # Steuerung für Relais
    if (abstand > min_abstand and abstand > 4):	#IF-Anweisung, wenn der Abstand kleiner als der max. Abstand
        relais.value(1)							#und größer 3cm istsoll Pumpe eingeschaltet werden und
        pumpe_status = "AN"						#Status-Meldung wird aus AN gestellt
    else:
        relais.value(0)							#ELSE-Anweisung, falls die Bedingungen nicht erfüllt sind,
        pumpe_status = "AUS"					#dann soll die Pumpe ausgeschaltet werden und Status-Meldung wird auf Aus gestellt        

    # Daten als JSON vorbereiten
    data = {
        "Fuellstand": round(fuellstand,2),		#Wert des Fuellstands wird mit zwei Nachkommastellen angegeben
        "Temperatur": round(temperatur,1),		#Wert der Temperatur wird mit einer Nachkommastelle angegeben
        "Status_Pumpe": pumpe_status
       }
    json_data = json.dumps(data)

    # JSON-Daten an das Topic senden
    client.publish(TOPIC_PUB, json_data)		#JSON-Daten werden an das entsprechende Topic gepublisht
    print(f"Daten gesendet: {json_data}")		#Ausgabe der JSON-Daten in der Konsole
    
    time.sleep(2)								#Nach 2 Sekunden beginnt die Schleife von vorne (einstellbar)


