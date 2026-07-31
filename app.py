import hmac
import os
from datetime import datetime, timezone

import flask
from dotenv import load_dotenv
from flask import jsonify, request

import db

load_dotenv()

app = flask.Flask(__name__)

# Runs on import, not just under `python app.py` - Granian imports this
# module directly under WSGI and never executes __main__, so init_db()
# has to happen here to run in production too.
db.init_db()

API_KEY = os.environ.get("API_KEY", "")

# Sanity bounds for a BME280 - catches sensor glitches (e.g. a bad I2C
# read) before they land in the data set, rather than validating for
# validation's sake.
VALID_RANGES = {
    "temperature_f": (-40, 150),
    "humidity": (0, 100),
    "pressure": (800, 1100),
}

REQUIRED_FIELDS = ["sensor_id", "temperature_f", "humidity", "pressure", "read_time"]


def is_authorized():
    supplied = request.headers.get("X-API-Key", "")
    # Fails closed: an unset API_KEY denies every write instead of
    # accidentally accepting anything.
    return bool(API_KEY) and hmac.compare_digest(supplied, API_KEY)


@app.route("/api/v1/health")
def health():
    return jsonify(status="ok")


@app.route("/api/v1/temperatures", methods=["POST"])
def create_reading():
    if not is_authorized():
        return jsonify(error="unauthorized"), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify(error="invalid or missing JSON body"), 400

    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        return jsonify(error=f"missing fields: {', '.join(missing)}"), 400

    for field, (low, high) in VALID_RANGES.items():
        value = data[field]
        if not isinstance(value, (int, float)) or not (low <= value <= high):
            return jsonify(error=f"{field} out of range"), 400

    received_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    reading_id = db.insert_reading(
        sensor_id=str(data["sensor_id"]),
        temperature_f=data["temperature_f"],
        humidity=data["humidity"],
        pressure=data["pressure"],
        read_time=data["read_time"],
        received_at=received_at,
    )

    return jsonify(status="ok", id=reading_id), 201


@app.route("/api/v1/temperatures/recent")
def recent_readings():
    hours = request.args.get("hours", default=24, type=int) or 24
    hours = max(1, min(hours, 720))  # clamp to [1 hour, 30 days]
    sensor_id = request.args.get("sensor_id")
    return jsonify(db.query_recent(hours=hours, sensor_id=sensor_id))


@app.route("/api/v1/temperatures/latest")
def latest_reading():
    sensor_id = request.args.get("sensor_id")
    reading = db.query_latest(sensor_id=sensor_id)
    if reading is None:
        return jsonify(error="no readings found"), 404
    return jsonify(reading)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004, debug=True)
