import unittest
import json
import os
import tempfile
from datetime import datetime
from app import app, get_current_readings, get_historical_data
from database import Database


class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary database."""
        # Create a temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Set environment variable for test database
        os.environ['DB_PATH'] = self.temp_db.name

        # Create test database instance
        self.test_db = Database(self.temp_db.name)

        # Initialize test database using context manager
        with self.test_db.db_session() as db:
            db.initialize_database()
            db.populate_sample_data()

        # Set up Flask test client
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary database file
        if hasattr(self, 'temp_db'):
            try:
                os.unlink(self.temp_db.name)
            except OSError:
                pass

    def test_index_route(self):
        """Test that the index route returns a 200 status code"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_health_check(self):
        """Test the health check endpoint"""
        response = self.app.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('message', data)
        self.assertIn('Environmental monitoring system', data['message'])
        self.assertIn('database', data)
        self.assertIn('readings_count', data['database'])

    def test_current_readings(self):
        """Test the current readings endpoint"""
        response = self.app.get('/api/readings/current')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertIn('timestamp', data)

        # Check that all required parameters are present
        readings = data['data']
        required_params = ['co2', 'vocs', 'pm25',
                           'pm10', 'temperature', 'humidity']
        for param in required_params:
            self.assertIn(param, readings)
            self.assertIsInstance(readings[param], (int, float))

    def test_historical_data_default(self):
        """Test the historical data endpoint with default parameters"""
        response = self.app.get('/api/api/readings')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertEqual(data['hours'], 24)
        self.assertIsInstance(data['data'], list)
        self.assertGreater(len(data['data']), 0)

    def test_historical_data_custom_hours(self):
        """Test the historical data endpoint with custom hours"""
        response = self.app.get('/readings?hours=6')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['hours'], 6)

    def test_historical_data_max_limit(self):
        """Test that historical data respects the maximum limit"""
        response = self.app.get('/readings?hours=200')  # Over the limit
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['hours'], 168)  # Should be capped at 1 week

    def test_parameters_info(self):
        """Test the parameters information endpoint"""
        response = self.app.get('/api/parameters')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('parameters', data)

        # Check that all required parameters are present
        required_params = ['co2', 'vocs', 'pm25',
                           'pm10', 'temperature', 'humidity']
        for param in required_params:
            self.assertIn(param, data['parameters'])
            param_info = data['parameters'][param]
            self.assertIn('name', param_info)
            self.assertIn('unit', param_info)
            self.assertIn('description', param_info)
            self.assertIn('normal_range', param_info)
            self.assertIn('dangerous_level', param_info)

    def test_database_stats(self):
        """Test the database stats endpoint"""
        response = self.app.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('stats', data)
        self.assertIn('total_readings', data['stats'])
        self.assertIn('database_type', data['stats'])
        self.assertGreater(data['stats']['total_readings'], 0)

    def test_get_current_readings(self):
        """Test the get_current_readings function"""
        readings = get_current_readings()
        self.assertIsNotNone(readings)
        required_fields = ['timestamp', 'co2', 'vocs',
                           'pm25', 'pm10', 'temperature', 'humidity']
        for field in required_fields:
            self.assertIn(field, readings)

    def test_get_historical_data(self):
        """Test the get_historical_data function"""
        data = get_historical_data(hours=6)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Check that data is within the specified time range
        if len(data) > 1:
            first_time = datetime.fromisoformat(data[0]['timestamp'])
            last_time = datetime.fromisoformat(data[-1]['timestamp'])
            time_diff = last_time - first_time
            # Allow small tolerance
            self.assertLessEqual(time_diff.total_seconds() / 3600, 6.1)

    def test_error_handling(self):
        """Test error handling in API endpoints"""
        # Test with invalid hours parameter
        response = self.app.get('/readings?hours=invalid')
        self.assertEqual(response.status_code, 200)  # Should handle gracefully

    def test_database_operations(self):
        """Test basic database operations"""
        with self.test_db.db_session() as db:
            # Test reading count
            count = db.get_reading_count()
            self.assertGreater(count, 0)

            # Test getting latest reading
            latest = db.get_latest_reading()
            self.assertIsNotNone(latest)
            self.assertIn('timestamp', latest)

            # Test getting readings since
            readings = db.get_readings_since(hours=1)
            self.assertIsInstance(readings, list)
            self.assertGreater(len(readings), 0)


class EnvironmentalMonitoringTestCase(unittest.TestCase):
    """Test cases for the environmental monitoring system."""

    def setUp(self):
        """Set up test client and database."""
        self.app = app.test_client()
        self.app.testing = True

        # Set up test database using in-memory database
        self.db = Database(':memory:')

        # Initialize database using context manager
        with self.db.db_session() as database:
            database.initialize_database()
            database.initialize_parameters()

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.app.get('/api/health')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('database', data)

    def test_current_readings(self):
        """Test the current readings endpoint."""
        response = self.app.get('/api/readings/current')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertIn('timestamp', data['data'])

    def test_historical_data(self):
        """Test the historical data endpoint."""
        response = self.app.get('/readings?hours=24')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertEqual(data['hours'], 24)

    def test_parameters_info(self):
        """Test the parameters info endpoint."""
        response = self.app.get('/api/parameters')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('parameters', data)
        self.assertIn('co2', data['parameters'])
        self.assertIn('temperature', data['parameters'])

    def test_admin_parameters_page(self):
        """Test the admin parameters page loads."""
        response = self.app.get('/admin/parameters')
        self.assertEqual(response.status_code, 200)

    def test_get_parameters_admin(self):
        """Test the admin parameters API endpoint."""
        response = self.app.get('/api/admin/parameters')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertIn('co2', data['data'])

    def test_update_parameter_admin(self):
        """Test updating a parameter via admin API."""
        # Test data for updating CO2 parameter
        update_data = {
            'display_name': 'Carbon Dioxide Updated',
            'unit': 'ppm',
            'description': 'Updated description for CO2',
            'normal_range_min': 350.0,
            'normal_range_max': 1200.0,
            'dangerous_level_min': None,
            'dangerous_level_max': 1200.0
        }

        response = self.app.put('/api/admin/parameters/co2',
                                data=json.dumps(update_data),
                                content_type='application/json')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'success')

    def test_update_parameter_validation(self):
        """Test parameter update validation."""
        # Test with invalid data (normal min >= max)
        invalid_data = {
            'display_name': 'Test',
            'unit': 'test',
            'description': 'Test description',
            'normal_range_min': 100.0,
            'normal_range_max': 50.0,  # Invalid: min > max
            'dangerous_level_min': None,
            'dangerous_level_max': None
        }

        response = self.app.put('/api/admin/parameters/co2',
                                data=json.dumps(invalid_data),
                                content_type='application/json')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['status'], 'error')

    def test_database_stats(self):
        """Test the database stats endpoint."""
        response = self.app.get('/api/stats')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'success')
        self.assertIn('stats', data)
        self.assertIn('total_readings', data['stats'])

    def test_index_page(self):
        """Test the main index page loads."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
