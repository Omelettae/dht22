import time
import math
import requests
import board # Pin Name Mapper of Pi5 GPIO From Adafruit
import adafruit_dht # DHT Library
from datetime import datetime

# DHT22 Sensor
name = "Pi4-2" # name in database
gpio = "D17" # Pi5 GPIO Pin
dht = adafruit_dht.DHT22(getattr(board, gpio))
url = "http://IP_of_pc_that_run_backend:5000/api/getDataDHT"

class API_Error(Exception):
	def __init__(self, message):
		super().__init__(message)

r = requests.get(url, timeout=5)
if r.status_code != 200:
	print(r)
	exit()



while True:

	# Datetime
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	try:
		temperature = dht.temperature
		humidity = dht.humidity
		vpd = 0.6108 * math.exp((17.27*temperature)/(temperature+237.3)) * (1-(humidity/100))
		
		data = {
			"sensorID": 6,
			"temperature": temperature,
			"humidity": humidity,
			"VPD": vpd,
			"time": timestamp
		}
	
		r = requests.post(url+"/api/getDataDHT", json=data, timeout=5) 
		if (r.status_code != 200):
			print(r)
			raise API_Error("r")
		print(f"{timestamp} ({name}) Temp: {temperature:.1f}°C Humidity: {humidity:.1f}% VPD: {vpd:.1f}kPa post: {r.status_code}")

	except Exception as e:
		data = {
			"sensorID": 6,
			"errorType": type(e).__name__,
			"errorMessage": str(e)
		}
		r= requests.post(url+"/api/ErrorLog", json=data, timeout=5)
		print(f"{timestamp} ({name}) Reading error:", e.args[0])

	time.sleep(2)
