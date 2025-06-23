from flask import Flask, render_template, jsonify, request
import os
import logging
import sys
from datetime import datetime
from database import db
import atexit
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'dev-secret-key-change-in-production')

# Global error handler for uncaught exceptions


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions to prevent crashes"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Handle graceful shutdown
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(
        exc_type, exc_value, exc_traceback))


# Set the exception handler
sys.excepthook = handle_uncaught_exception


def get_current_readings():
    """Get the most recent environmental readings from database"""
    try:
        latest = db.get_latest_reading()
        if latest:
            return latest
        else:
            # Return default values if no data exists
            return {
                'timestamp': datetime.now().isoformat(),
                'co2': 0,
                'vocs': 0,
                'pm25': 0,
                'pm10': 0,
                'temperature': 0,
                'humidity': 0
            }
    except Exception as e:
        logger.error(f"Error getting current readings: {e}", exc_info=True)
        return None


def get_historical_data(hours=24):
    """Get historical data for the specified number of hours from database"""
    try:
        return db.get_readings_since(hours)
    except Exception as e:
        logger.error(f"Error getting historical data: {e}", exc_info=True)
        return []


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        reading_count = db.get_reading_count()

        return jsonify({
            'status': 'healthy',
            'message': 'Environmental monitoring system is running!',
            'database': {
                'type': 'sqlite',
                'readings_count': reading_count
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }), 500


@app.route('/api/current')
def current_readings():
    """Get current environmental readings"""
    try:
        readings = get_current_readings()
        if readings:
            return jsonify({
                'status': 'success',
                'data': readings,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to retrieve current readings'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/historical')
def historical_data():
    """Get historical environmental data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        if hours > 168:  # Limit to 1 week
            hours = 168

        data = get_historical_data(hours)
        return jsonify({
            'status': 'success',
            'data': data,
            'hours': hours
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/parameters')
def parameters_info():
    """Get information about monitored parameters"""
    try:
        parameters = db.get_all_parameters()

        return jsonify({
            'status': 'success',
            'data': parameters
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/admin/parameters')
def admin_parameters():
    """Admin page for editing parameter thresholds"""
    return render_template('admin_parameters.html')


@app.route('/api/admin/parameters', methods=['GET'])
def get_parameters_admin():
    """Get parameters for admin interface"""
    try:
        parameters = db.get_all_parameters()

        return jsonify({
            'status': 'success',
            'data': parameters
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/admin/parameters/<param_name>', methods=['PUT'])
def update_parameter_admin(param_name):
    """Update a parameter's configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Validate required fields
        required_fields = ['display_name', 'unit',
                           'description', 'normal_range_min', 'normal_range_max']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Validate numeric fields
        try:
            normal_min = float(data['normal_range_min'])
            normal_max = float(data['normal_range_max'])
            dangerous_min = float(data.get('dangerous_level_min', 0)) if data.get(
                'dangerous_level_min') else None
            dangerous_max = float(data.get('dangerous_level_max', 0)) if data.get(
                'dangerous_level_max') else None
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'Invalid numeric values'
            }), 400

        # Validate ranges
        if normal_min >= normal_max:
            return jsonify({
                'status': 'error',
                'message': 'Normal range min must be less than max'
            }), 400

        if dangerous_min is not None and dangerous_max is not None and dangerous_min >= dangerous_max:
            return jsonify({
                'status': 'error',
                'message': 'Dangerous level min must be less than max'
            }), 400

        updates = {
            'display_name': data['display_name'],
            'unit': data['unit'],
            'description': data['description'],
            'normal_range_min': normal_min,
            'normal_range_max': normal_max,
            'dangerous_level_min': dangerous_min,
            'dangerous_level_max': dangerous_max
        }

        success = db.update_parameter(param_name, updates)

        if success:
            return jsonify({
                'status': 'success',
                'message': f'Parameter {param_name} updated successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to update parameter {param_name}'
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/stats')
def database_stats():
    """Get database statistics"""
    try:
        reading_count = db.get_reading_count()
        latest_reading = db.get_latest_reading()

        return jsonify({
            'status': 'success',
            'stats': {
                'total_readings': reading_count,
                'latest_reading_timestamp': latest_reading['timestamp'] if latest_reading else None,
                'database_type': 'sqlite'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/alerts')
def get_virtual_alerts():
    """Get virtual alerts based on current environmental conditions"""
    try:
        # Get current readings
        current_readings = get_current_readings()
        if not current_readings:
            return jsonify({
                'status': 'error',
                'message': 'No current readings available'
            }), 500

        # Get parameter thresholds
        parameters = db.get_all_parameters()

        alerts = []

        # Analyze CO2 levels for ventilation alerts
        co2_value = current_readings.get('co2', 0)
        co2_params = parameters.get('co2', {})

        if co2_value > co2_params.get('normal_range_max', 1000):
            if co2_value > co2_params.get('dangerous_level_max', 1000):
                alerts.append({
                    'type': 'ventilation_required',
                    'severity': 'high',
                    'title': '🚨 Immediate Ventilation Required',
                    'message': f'CO2 levels are dangerously high ({co2_value} ppm). Open windows immediately and increase ventilation.',
                    'parameter': 'CO2',
                    'value': co2_value,
                    'threshold': co2_params.get('dangerous_level_max', 1000)
                })
            else:
                alerts.append({
                    'type': 'ventilation_required',
                    'severity': 'medium',
                    'title': '🪟 Ventilation Recommended',
                    'message': f'CO2 levels are elevated ({co2_value} ppm). Consider opening windows for better air circulation.',
                    'parameter': 'CO2',
                    'value': co2_value,
                    'threshold': co2_params.get('normal_range_max', 1000)
                })

        # Analyze VOCs for ventilation alerts
        vocs_value = current_readings.get('vocs', 0)
        vocs_params = parameters.get('vocs', {})

        if vocs_value > vocs_params.get('normal_range_max', 500):
            if vocs_value > vocs_params.get('dangerous_level_max', 500):
                alerts.append({
                    'type': 'ventilation_required',
                    'severity': 'high',
                    'title': '🚨 High VOC Levels Detected',
                    'message': f'VOC levels are dangerously high ({vocs_value} ppb). Increase ventilation and check for sources.',
                    'parameter': 'VOCs',
                    'value': vocs_value,
                    'threshold': vocs_params.get('dangerous_level_max', 500)
                })
            else:
                alerts.append({
                    'type': 'ventilation_required',
                    'severity': 'medium',
                    'title': '🪟 VOC Levels Elevated',
                    'message': f'VOC levels are elevated ({vocs_value} ppb). Consider improving ventilation.',
                    'parameter': 'VOCs',
                    'value': vocs_value,
                    'threshold': vocs_params.get('normal_range_max', 500)
                })

        # Analyze PM2.5 for air quality alerts
        pm25_value = current_readings.get('pm25', 0)
        pm25_params = parameters.get('pm25', {})

        if pm25_value > pm25_params.get('normal_range_max', 12):
            if pm25_value > pm25_params.get('dangerous_level_max', 35):
                alerts.append({
                    'type': 'air_quality',
                    'severity': 'high',
                    'title': '🚨 Poor Air Quality - PM2.5',
                    'message': f'PM2.5 levels are dangerously high ({pm25_value} μg/m³). Improve air filtration and ventilation.',
                    'parameter': 'PM2.5',
                    'value': pm25_value,
                    'threshold': pm25_params.get('dangerous_level_max', 35)
                })
            else:
                alerts.append({
                    'type': 'air_quality',
                    'severity': 'medium',
                    'title': '⚠️ Moderate Air Quality - PM2.5',
                    'message': f'PM2.5 levels are elevated ({pm25_value} μg/m³). Monitor air quality.',
                    'parameter': 'PM2.5',
                    'value': pm25_value,
                    'threshold': pm25_params.get('normal_range_max', 12)
                })

        # Analyze PM10 for air quality alerts
        pm10_value = current_readings.get('pm10', 0)
        pm10_params = parameters.get('pm10', {})

        if pm10_value > pm10_params.get('normal_range_max', 54):
            if pm10_value > pm10_params.get('dangerous_level_max', 150):
                alerts.append({
                    'type': 'air_quality',
                    'severity': 'high',
                    'title': '🚨 Poor Air Quality - PM10',
                    'message': f'PM10 levels are dangerously high ({pm10_value} μg/m³). Improve air filtration and ventilation.',
                    'parameter': 'PM10',
                    'value': pm10_value,
                    'threshold': pm10_params.get('dangerous_level_max', 150)
                })
            else:
                alerts.append({
                    'type': 'air_quality',
                    'severity': 'medium',
                    'title': '⚠️ Moderate Air Quality - PM10',
                    'message': f'PM10 levels are elevated ({pm10_value} μg/m³). Monitor air quality.',
                    'parameter': 'PM10',
                    'value': pm10_value,
                    'threshold': pm10_params.get('normal_range_max', 54)
                })

        # Analyze temperature for comfort alerts
        temp_value = current_readings.get('temperature', 0)
        temp_params = parameters.get('temperature', {})

        if temp_value < temp_params.get('normal_range_min', 18) or temp_value > temp_params.get('normal_range_max', 25):
            if temp_value < temp_params.get('dangerous_level_min', 10) or temp_value > temp_params.get('dangerous_level_max', 30):
                alerts.append({
                    'type': 'comfort',
                    'severity': 'high',
                    'title': '🌡️ Extreme Temperature',
                    'message': f'Temperature is outside comfortable range ({temp_value}°C). Adjust HVAC settings.',
                    'parameter': 'Temperature',
                    'value': temp_value,
                    'threshold': f"{temp_params.get('normal_range_min', 18)}-{temp_params.get('normal_range_max', 25)}°C"
                })
            else:
                alerts.append({
                    'type': 'comfort',
                    'severity': 'medium',
                    'title': '🌡️ Temperature Alert',
                    'message': f'Temperature is outside optimal range ({temp_value}°C). Consider adjusting settings.',
                    'parameter': 'Temperature',
                    'value': temp_value,
                    'threshold': f"{temp_params.get('normal_range_min', 18)}-{temp_params.get('normal_range_max', 25)}°C"
                })

        # Analyze humidity for comfort alerts
        humidity_value = current_readings.get('humidity', 0)
        humidity_params = parameters.get('humidity', {})

        if humidity_value < humidity_params.get('normal_range_min', 30) or humidity_value > humidity_params.get('normal_range_max', 60):
            if humidity_value < humidity_params.get('dangerous_level_min', 20) or humidity_value > humidity_params.get('dangerous_level_max', 80):
                alerts.append({
                    'type': 'comfort',
                    'severity': 'high',
                    'title': '💧 Extreme Humidity',
                    'message': f'Humidity is outside comfortable range ({humidity_value}%). Adjust humidity control.',
                    'parameter': 'Humidity',
                    'value': humidity_value,
                    'threshold': f"{humidity_params.get('normal_range_min', 30)}-{humidity_params.get('normal_range_max', 60)}%"
                })
            else:
                alerts.append({
                    'type': 'comfort',
                    'severity': 'medium',
                    'title': '💧 Humidity Alert',
                    'message': f'Humidity is outside optimal range ({humidity_value}%). Consider adjusting settings.',
                    'parameter': 'Humidity',
                    'value': humidity_value,
                    'threshold': f"{humidity_params.get('normal_range_min', 30)}-{humidity_params.get('normal_range_max', 60)}%"
                })

        # Sort alerts by severity (high first, then medium)
        alerts.sort(key=lambda x: 0 if x['severity'] == 'high' else 1)

        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'total_alerts': len(alerts),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error generating alerts: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Global error handlers to prevent crashes
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors gracefully"""
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'API endpoint not found'
        }), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors gracefully"""
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
    return render_template('500.html'), 500


@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {error}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }), 500
    return render_template('500.html'), 500


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    cleanup_database()
    exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def cleanup_database():
    """Cleanup database connection on application shutdown"""
    try:
        db.disconnect()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")


# Register cleanup function
atexit.register(cleanup_database)

if __name__ == '__main__':
    # Initialize database connection
    try:
        db.connect()
        db.initialize_database()
        db.initialize_parameters()
        logger.info("Database and parameters initialized successfully")
    except Exception as e:
        logger.error(
            f"Warning: Database initialization failed: {e}", exc_info=True)
        logger.info(
            "You may need to run 'python init_db.py' to set up the database")

    logger.info("Starting Flask application on http://0.0.0.0:8000")
    app.run(debug=True, host='0.0.0.0', port=8000)
