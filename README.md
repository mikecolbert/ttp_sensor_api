# ttp_sensor_api

API application for [thetemperatureproject.org](https://thetemperatureproject.org)

Receives temperature/humidity/pressure readings from an ESP32 + BME280 sensor
and serves them back out for the dashboard. Data is stored in SQLite.

---

## To Run This Application On Your Local Computer

1. Clone this repository to your local computer

2. Create a new virtual environment
   - Windows: `python -m venv ./venv`
   - Mac: `python3 -m venv ./venv`

3. Activate the new virtual environment
   - Windows: `.\venv\Scripts\activate`
   - Mac: `source ./venv/bin/activate`

4. Install the dependencies `pip install -r requirements.txt`

5. Copy `.env.example` to `.env` and set `API_KEY` to any value for local
   testing (e.g. `openssl rand -hex 32`)

6. Run the application with `python app.py`

The app creates `sensors.db` in the working directory on first run.

---

## API Contract

### `POST /api/v1/temperatures`

Write a reading. Requires header `X-API-Key: <value from .env>`.

```json
{
  "sensor_id": "0",
  "temperature_f": 72.3,
  "humidity": 45.2,
  "pressure": 1013.2,
  "read_time": "2026-07-31 16:23:45"
}
```

`read_time` is UTC, `"YYYY-MM-DD HH:MM:SS"`, set by the device's NTP-synced
clock. Valid ranges: `temperature_f` -40 to 150, `humidity` 0-100, `pressure`
800-1100 hPa - readings outside this are rejected as sensor glitches.

Responses: `201 {"status": "ok", "id": 123}` on success · `400` bad payload ·
`401` bad/missing key.

### `GET /api/v1/temperatures/recent?hours=24&sensor_id=0`

Public, no auth. Returns a JSON array of readings, oldest to newest.
`hours` defaults to 24 (clamped 1-720). `sensor_id` is optional.

### `GET /api/v1/temperatures/latest?sensor_id=0`

Public, no auth. Returns the single most recent reading, or `404` if none.

### `GET /api/v1/health`

Public, no auth. Returns `200 {"status": "ok"}` - used for the Docker
healthcheck once containerized.

---

## Testing locally with curl

```bash
# Write a reading
curl -s -w "\nhttp status: %{http_code}\n" -X POST https://thetemperatureproject.org/api/v1/temperatures \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your api key here> " \
  -d '{"sensor_id":"99","temperature_f":72.3,"humidity":45.2,"pressure":1013.2,"read_time":"2026-07-31 16:23:45"}'

# Read it back
curl -s https://thetemperatureproject.org/api/v1/temperatures/recent
curl -s https://thetemperatureproject.org/api/v1/temperatures/latest
```

---

## TODO

[ ] Firmware (`final.ino`) uses `client.setInsecure()`, skipping TLS
certificate validation on its connection to this API. Now that the
connection carries a real secret (`X-API-Key`) on every request, an
unvalidated TLS connection means that key could be exposed to a
man-in-the-middle. Fix is to pin the Let's Encrypt root CA on the
device via `setCACert()` - more involved since the cert rotates on
Let's Encrypt's renewal schedule.
