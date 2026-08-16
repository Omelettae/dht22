"""
DHT22 x3 offset/accuracy test logger
-------------------------------------
Reads three DHT22 sensors (GPIO17, GPIO27, GPIO22) as close to
simultaneously as possible (using threads) and logs raw readings
to a CSV file for offset comparison.

Run on the Raspberry Pi 5 with the sensors wired to the pins below.
"""

import time
import csv
import os
import threading
from datetime import datetime

import board
import adafruit_dht

# ----------------------------------------------------------------
# Config
# ----------------------------------------------------------------
SENSORS = {
    "gpio17": "D17",
    "gpio27": "D27",
    "gpio22": "D22",
}

CSV_PATH = "dht22_offset_test.csv"
READ_INTERVAL_S = 2.0        # DHT22 min ~2s between reads per sensor
RETRIES_PER_SENSOR = 2       # retry a couple times if a read glitches out
RETRY_DELAY_S = 0.5

# ----------------------------------------------------------------
# Sensor init
# ----------------------------------------------------------------
dht_objs = {
    name: adafruit_dht.DHT22(getattr(board, pin), use_pulseio=True)
    for name, pin in SENSORS.items()
}

CSV_FIELDS = [
    "timestamp",
    "elapsed_s",
    "temp_gpio17_c", "temp_gpio27_c", "temp_gpio22_c",
    "humidity_gpio17_pct", "humidity_gpio27_pct", "humidity_gpio22_pct",
    "error_gpio17", "error_gpio27", "error_gpio22",
    "read_latency_gpio17_ms", "read_latency_gpio27_ms", "read_latency_gpio22_ms",
]


def init_csv(path):
    file_exists = os.path.isfile(path)
    if not file_exists:
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()


def read_sensor(name, results):
    """Read one sensor with retries, store raw result + timing + error."""
    dht = dht_objs[name]
    last_err = ""
    for attempt in range(RETRIES_PER_SENSOR + 1):
        t0 = time.perf_counter()
        try:
            temp = dht.temperature
            hum = dht.humidity
            latency_ms = (time.perf_counter() - t0) * 1000
            if temp is None or hum is None:
                raise RuntimeError("Sensor returned None")
            results[name] = {
                "temp": temp,
                "hum": hum,
                "error": "",
                "latency_ms": latency_ms,
            }
            return
        except RuntimeError as e:
            last_err = str(e)
            time.sleep(RETRY_DELAY_S)
        except Exception as e:
            last_err = f"FATAL: {e}"
            break

    latency_ms = (time.perf_counter() - t0) * 1000
    results[name] = {
        "temp": "",
        "hum": "",
        "error": last_err,
        "latency_ms": latency_ms,
    }


def read_all_sensors_concurrently():
    """Fire off a thread per sensor so all three reads start
    within microseconds of each other, minimizing time skew."""
    results = {}
    threads = [
        threading.Thread(target=read_sensor, args=(name, results))
        for name in SENSORS
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def main():
    init_csv(CSV_PATH)
    start_time = time.monotonic()

    print(f"Logging to {os.path.abspath(CSV_PATH)}  (Ctrl+C to stop)\n")

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            elapsed_s = round(time.monotonic() - start_time, 3)

            results = read_all_sensors_concurrently()

            row = {
                "timestamp": timestamp,
                "elapsed_s": elapsed_s,
                "temp_gpio17_c": results["gpio17"]["temp"],
                "temp_gpio27_c": results["gpio27"]["temp"],
                "temp_gpio22_c": results["gpio22"]["temp"],
                "humidity_gpio17_pct": results["gpio17"]["hum"],
                "humidity_gpio27_pct": results["gpio27"]["hum"],
                "humidity_gpio22_pct": results["gpio22"]["hum"],
                "error_gpio17": results["gpio17"]["error"],
                "error_gpio27": results["gpio27"]["error"],
                "error_gpio22": results["gpio22"]["error"],
                "read_latency_gpio17_ms": round(results["gpio17"]["latency_ms"], 1),
                "read_latency_gpio27_ms": round(results["gpio27"]["latency_ms"], 1),
                "read_latency_gpio22_ms": round(results["gpio22"]["latency_ms"], 1),
            }

            with open(CSV_PATH, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writerow(row)

            # Console preview
            def fmt(v):
                return f"{v:.6f}" if isinstance(v, float) else (v or "ERR")

            print(
                f"{timestamp} | "
                f"T17={fmt(results['gpio17']['temp'])} "
                f"T27={fmt(results['gpio27']['temp'])} "
                f"T22={fmt(results['gpio22']['temp'])} | "
                f"H17={fmt(results['gpio17']['hum'])} "
                f"H27={fmt(results['gpio27']['hum'])} "
                f"H22={fmt(results['gpio22']['hum'])}"
            )

            time.sleep(READ_INTERVAL_S)

    except KeyboardInterrupt:
        print("\nStopped. Data saved to", os.path.abspath(CSV_PATH))
    finally:
        for dht in dht_objs.values():
            try:
                dht.exit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
