import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "sensors.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id     TEXT NOT NULL,
    temperature_f REAL NOT NULL,
    humidity      REAL NOT NULL,
    pressure      REAL NOT NULL,
    read_time     TEXT NOT NULL,
    received_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_time ON readings(sensor_id, read_time);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # WAL mode lets dashboard reads happen without blocking on the
    # ESP32's writes (and vice versa) - see README for why SQLite
    # is the right fit for a single-writer sensor feed like this one.
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def insert_reading(sensor_id, temperature_f, humidity, pressure, read_time, received_at):
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO readings
               (sensor_id, temperature_f, humidity, pressure, read_time, received_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sensor_id, temperature_f, humidity, pressure, read_time, received_at),
        )
        return cursor.lastrowid


def query_recent(hours=24, sensor_id=None):
    query = """SELECT id, sensor_id, temperature_f, humidity, pressure, read_time
               FROM readings
               WHERE read_time >= datetime('now', ?)"""
    params = [f"-{hours} hours"]
    if sensor_id:
        query += " AND sensor_id = ?"
        params.append(sensor_id)
    query += " ORDER BY read_time ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def query_latest(sensor_id=None):
    query = """SELECT id, sensor_id, temperature_f, humidity, pressure, read_time
               FROM readings"""
    params = []
    if sensor_id:
        query += " WHERE sensor_id = ?"
        params.append(sensor_id)
    query += " ORDER BY read_time DESC LIMIT 1"
    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
