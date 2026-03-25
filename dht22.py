import time
import math
import requests
import board # Pin Name Mapper of Pi5 GPIO From Adafruit
import adafruit_dht # DHT Library
from datetime import datetime

# DHT22 Sensor
gpio = "D17" # Pi5 GPIO Pin
dht = adafruit_dht.DHT22(getattr(board, gpio))
url = "http://IP_of_pc_that_run_backend:5000/api/getDataDHT"
error = "http://IP_of_pc_that_run_backend:5000/api/ErrorLog"

while True:

	# Datetime
	timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	try:
		temperature = dht.temperature
		humidity = dht.humidity
		vpd = 0.6108 * math.exp((17.27*temperature)/(temperature+237.3)) * (1-(humidity/100))
		
		data = {
			"sensorID": 1,
			"temperature": temperature,
			"humidity": humidity,
			"VPD": vpd,
			"time": timestamp
		}
		
		r = requests.post(url, json=data, timeout=5) 
		if (r.status_code != 200):
			print(r)
			break
		print(f"{timestamp} ({gpio}) Temp: {temperature:.1f}°C Humidity: {humidity:.1f}% VPD: {vpd:.1f}kPa post: {r.status_code}")

	except RuntimeError as error:
		print(f"{timestamp} ({gpio}) Reading error:", error.args[0])
		ErrorData = {
			"sensorID": 1,
			"errorType": "RuntimeError",
			"errorMessage": error.args[0],
			"createdAt": timestamp
		}
		r = requests.post(error, json=ErrorData, timeout=5) 
	except Exception as e:
		print("Error:", e)

	time.sleep(2)
