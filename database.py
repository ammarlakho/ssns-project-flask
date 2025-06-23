"""Direct SQLite database operations for the environmental monitoring system."""

import sqlite3
import random
import os
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """Direct SQLite database implementation with thread-safe connection management."""

    def __init__(self, db_path: str = None):
        """Initialize database with path."""
        self.db_path = db_path or os.environ.get(
            'DB_PATH', 'environmental_data.db')
        self._lock = threading.Lock()
        self._connection = None

    def connect(self) -> None:
        """Establish SQLite database connection."""
        with self._lock:
            try:
                if self._connection is None:
                    self._connection = sqlite3.connect(
                        self.db_path, check_same_thread=False, timeout=30.0)
                    # Enable foreign keys and set row factory for dict-like access
                    self._connection.execute("PRAGMA foreign_keys = ON")
                    self._connection.execute("PRAGMA journal_mode = WAL")
                    self._connection.execute("PRAGMA synchronous = NORMAL")
                    self._connection.row_factory = sqlite3.Row
                    logger.debug("Database connection established")
            except sqlite3.Error as e:
                logger.error(
                    f"Failed to connect to SQLite database: {e}", exc_info=True)
                raise Exception(f"Failed to connect to SQLite database: {e}")

    def disconnect(self) -> None:
        """Close SQLite database connection."""
        with self._lock:
            try:
                if self._connection:
                    self._connection.close()
                    self._connection = None
                    logger.debug("Database connection closed")
            except Exception as e:
                logger.error(
                    f"Error closing database connection: {e}", exc_info=True)

    @property
    def connection(self):
        """Get the current database connection, creating it if necessary."""
        if self._connection is None:
            self.connect()
        return self._connection

    @contextmanager
    def db_session(self):
        """Context manager for database connections with better error handling."""
        connection_created = False
        try:
            # Ensure we have a connection
            if self._connection is None:
                self.connect()
                connection_created = True

            # Test the connection
            self._connection.execute("SELECT 1")

            yield self
        except sqlite3.Error as e:
            logger.error(f"Database session error: {e}", exc_info=True)
            # If connection is broken, try to reconnect
            if connection_created or "database is locked" in str(e).lower():
                try:
                    self.disconnect()
                    self.connect()
                    yield self
                except Exception as reconnect_error:
                    logger.error(
                        f"Failed to reconnect to database: {reconnect_error}", exc_info=True)
                    raise
            else:
                raise
        except Exception as e:
            logger.error(
                f"Unexpected database session error: {e}", exc_info=True)
            raise
        finally:
            # Only close if we created the connection in this session
            if connection_created:
                self.disconnect()

    def _ensure_connection(self):
        """Ensure database connection is available and working."""
        try:
            if self._connection is None:
                self.connect()
            else:
                # Test if connection is still valid
                self._connection.execute("SELECT 1")
        except sqlite3.Error:
            # Connection is broken, recreate it
            self.disconnect()
            self.connect()

    def initialize_database(self) -> None:
        """Initialize SQLite database tables and schema."""
        try:
            cursor = self.connection.cursor()

            # Create environmental readings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS environmental_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    co2 REAL NOT NULL,
                    vocs REAL NOT NULL,
                    pm25 REAL NOT NULL,
                    pm10 REAL NOT NULL,
                    temperature REAL NOT NULL,
                    humidity REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create parameters table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parameters (
                    name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    description TEXT NOT NULL,
                    normal_range_min REAL NOT NULL,
                    normal_range_max REAL NOT NULL,
                    dangerous_level_min REAL,
                    dangerous_level_max REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create index on timestamp for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON environmental_readings(timestamp)
            ''')

            self.connection.commit()

        except sqlite3.Error as e:
            raise Exception(f"Failed to initialize database: {e}")

    def initialize_parameters(self) -> None:
        """Initialize default parameter configurations."""
        try:
            cursor = self.connection.cursor()

            # Check if parameters already exist
            cursor.execute('SELECT COUNT(*) FROM parameters')
            if cursor.fetchone()[0] > 0:
                return  # Parameters already initialized

            # Default parameter configurations
            default_params = [
                ('co2', 'Carbon Dioxide', 'ppm',
                 'Concentration of carbon dioxide in the air', 400, 1000, None, 1000),
                ('vocs', 'Volatile Organic Compounds', 'ppb',
                 'Concentration of volatile organic compounds', 0, 500, None, 500),
                ('pm25', 'PM2.5', 'μg/m³',
                 'Fine particulate matter (2.5 micrometers or smaller)', 0, 12, None, 35),
                ('pm10', 'PM10', 'μg/m³',
                 'Coarse particulate matter (10 micrometers or smaller)', 0, 54, None, 150),
                ('temperature', 'Temperature', '°C',
                 'Ambient air temperature', 18, 25, 10, 30),
                ('humidity', 'Relative Humidity', '%',
                 'Relative humidity of the air', 30, 60, 20, 80)
            ]

            cursor.executemany('''
                INSERT OR IGNORE INTO parameters 
                (name, display_name, unit, description, normal_range_min, normal_range_max, dangerous_level_min, dangerous_level_max)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', default_params)

            self.connection.commit()

        except sqlite3.Error as e:
            raise Exception(f"Failed to initialize parameters: {e}")

    def get_all_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get all parameter configurations."""
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()
            cursor.execute('''
                SELECT name, display_name, unit, description, 
                       normal_range_min, normal_range_max, 
                       dangerous_level_min, dangerous_level_max
                FROM parameters
                ORDER BY name
            ''')

            rows = cursor.fetchall()
            parameters = {}

            for row in rows:
                param_dict = dict(row)
                # Format ranges for display
                normal_range = f"{param_dict['normal_range_min']}-{param_dict['normal_range_max']}"

                if param_dict['dangerous_level_min'] is not None and param_dict['dangerous_level_max'] is not None:
                    dangerous_level = f"<{param_dict['dangerous_level_min']} or >{param_dict['dangerous_level_max']}"
                elif param_dict['dangerous_level_max'] is not None:
                    dangerous_level = f">{param_dict['dangerous_level_max']}"
                else:
                    dangerous_level = "N/A"

                parameters[param_dict['name']] = {
                    'name': param_dict['display_name'],
                    'unit': param_dict['unit'],
                    'description': param_dict['description'],
                    'normal_range': normal_range,
                    'dangerous_level': dangerous_level,
                    'normal_range_min': param_dict['normal_range_min'],
                    'normal_range_max': param_dict['normal_range_max'],
                    'dangerous_level_min': param_dict['dangerous_level_min'],
                    'dangerous_level_max': param_dict['dangerous_level_max']
                }

            return parameters

        except sqlite3.Error as e:
            logger.error(f"Failed to get parameters: {e}")
            return {}

    def update_parameter(self, param_name: str, updates: Dict[str, Any]) -> bool:
        """Update a parameter's configuration."""
        cursor = None
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()

            # Build update query dynamically
            update_fields = []
            values = []

            for field, value in updates.items():
                if field in ['display_name', 'unit', 'description', 'normal_range_min',
                             'normal_range_max', 'dangerous_level_min', 'dangerous_level_max']:
                    update_fields.append(f"{field} = ?")
                    values.append(value)

            if not update_fields:
                return False

            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(param_name)

            query = f'''
                UPDATE parameters 
                SET {', '.join(update_fields)}
                WHERE name = ?
            '''

            cursor.execute(query, values)
            self._connection.commit()

            return cursor.rowcount > 0

        except sqlite3.Error as e:
            logger.error(f"Failed to update parameter: {e}")
            return False

    def insert_reading(self, reading: Dict[str, Any]) -> bool:
        """Insert a new environmental reading."""
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()
            cursor.execute('''
                INSERT INTO environmental_readings 
                (timestamp, co2, vocs, pm25, pm10, temperature, humidity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                reading['timestamp'],
                reading['co2'],
                reading['vocs'],
                reading['pm25'],
                reading['pm10'],
                reading['temperature'],
                reading['humidity']
            ))
            self._connection.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to insert reading: {e}")
            return False

    def get_latest_reading(self) -> Optional[Dict[str, Any]]:
        """Get the most recent environmental reading."""
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()
            cursor.execute('''
                SELECT timestamp, co2, vocs, pm25, pm10, temperature, humidity
                FROM environmental_readings
                ORDER BY timestamp DESC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get latest reading: {e}")
            return None

    def get_readings_since(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get readings from the last N hours."""
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor.execute('''
                SELECT timestamp, co2, vocs, pm25, pm10, temperature, humidity
                FROM environmental_readings
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (cutoff_time,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get readings since: {e}")
            return []

    def get_readings_between(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get readings between two timestamps."""
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()
            cursor.execute('''
                SELECT timestamp, co2, vocs, pm25, pm10, temperature, humidity
                FROM environmental_readings
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            ''', (start_time.isoformat(), end_time.isoformat()))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get readings between: {e}")
            return []

    def get_reading_count(self) -> int:
        """Get total number of readings in the database."""
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM environmental_readings')
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Failed to get reading count: {e}")
            return 0

    def clear_old_readings(self, days: int = 30) -> int:
        """Clear readings older than N days. Returns number of deleted records."""
        try:
            self._ensure_connection()
            cursor = self._connection.cursor()
            cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute('''
                DELETE FROM environmental_readings
                WHERE timestamp < ?
            ''', (cutoff_time,))

            deleted_count = cursor.rowcount
            self._connection.commit()
            return deleted_count
        except sqlite3.Error as e:
            logger.error(f"Failed to clear old readings: {e}")
            return 0

    def populate_sample_data(self) -> None:
        """Populate database with sample data for testing/demo."""
        try:
            # Generate sample data for the last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)

            # Generate readings every 15 minutes
            current_time = start_time
            while current_time <= end_time:
                # Create some variation to test alerts
                hour = current_time.hour

                # Simulate different scenarios throughout the day
                if 8 <= hour <= 10:  # Morning - normal conditions
                    reading = {
                        'timestamp': current_time.isoformat(),
                        'co2': random.uniform(400, 600),
                        'vocs': random.uniform(50, 150),
                        'pm25': random.uniform(5, 10),
                        'pm10': random.uniform(10, 20),
                        'temperature': random.uniform(20, 23),
                        'humidity': random.uniform(45, 55)
                    }
                elif 11 <= hour <= 13:  # Midday - elevated CO2 and VOCs
                    reading = {
                        'timestamp': current_time.isoformat(),
                        # Will trigger ventilation alerts
                        'co2': random.uniform(800, 1200),
                        # Will trigger VOC alerts
                        'vocs': random.uniform(300, 600),
                        'pm25': random.uniform(8, 15),
                        'pm10': random.uniform(15, 25),
                        'temperature': random.uniform(22, 26),
                        'humidity': random.uniform(50, 65)
                    }
                elif 14 <= hour <= 16:  # Afternoon - poor air quality
                    reading = {
                        'timestamp': current_time.isoformat(),
                        'co2': random.uniform(600, 900),
                        'vocs': random.uniform(200, 400),
                        # Will trigger PM2.5 alerts
                        'pm25': random.uniform(15, 40),
                        # Will trigger PM10 alerts
                        'pm10': random.uniform(30, 80),
                        'temperature': random.uniform(24, 28),
                        'humidity': random.uniform(55, 70)
                    }
                elif 17 <= hour <= 19:  # Evening - temperature/humidity issues
                    reading = {
                        'timestamp': current_time.isoformat(),
                        'co2': random.uniform(500, 700),
                        'vocs': random.uniform(100, 250),
                        'pm25': random.uniform(6, 12),
                        'pm10': random.uniform(12, 22),
                        # Will trigger temperature alerts
                        'temperature': random.uniform(26, 32),
                        # Will trigger humidity alerts
                        'humidity': random.uniform(70, 85)
                    }
                else:  # Night - normal conditions
                    reading = {
                        'timestamp': current_time.isoformat(),
                        'co2': random.uniform(400, 500),
                        'vocs': random.uniform(30, 100),
                        'pm25': random.uniform(3, 8),
                        'pm10': random.uniform(8, 15),
                        'temperature': random.uniform(18, 22),
                        'humidity': random.uniform(40, 50)
                    }

                self.insert_reading(reading)
                current_time += timedelta(minutes=15)

        except Exception as e:
            print(f"Failed to populate sample data: {e}")


# Global database instance
db = Database()
