from flask import Flask, render_template, jsonify, request, make_response
import os
import logging
import sys
import csv
import io
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
    """Get the most recent environmental readings from database with status and alerts"""
    try:
        latest = db.get_latest_reading()
        if latest:
            # Analyze the reading to get status and alerts
            analyzed_data = db.analyze_reading_with_status(latest)
            return {
                'timestamp': latest['timestamp'],
                'parameters': analyzed_data
            }
        else:
            # Throw an error if no latest reading is found
            raise Exception("No latest reading found")
    except Exception as e:
        logger.error(f"Error getting current readings: {e}", exc_info=True)
        return None


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


@app.route('/api/readings/current',  methods=['GET'])
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


@app.route('/api/readings',  methods=['GET'])
def historical_data():
    """Get historical environmental data"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({
                'status': 'error',
                'message': 'Both start_date and end_date are required'
            }), 400

        try:
            start_date = datetime.fromisoformat(
                start_date_str.replace('T', ' '))
            end_date = datetime.fromisoformat(
                end_date_str.replace('T', ' '))
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DDTHH:MM format'
            }), 400

        # Validate date range
        if start_date >= end_date:
            return jsonify({
                'status': 'error',
                'message': 'Start date must be before end date'
            }), 400

        # Limit the date range to prevent excessive data
        date_diff = end_date - start_date
        if date_diff.days > 365:  # Limit to 1 year
            return jsonify({
                'status': 'error',
                'message': 'Date range cannot exceed 1 year'
            }), 400

        # Get readings using date range
        data = db.get_readings_between(start_date, end_date)

        return jsonify({
            'status': 'success',
            'data': data,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'count': len(data)
        })
    except Exception as e:
        logger.error(f"Error getting historical data: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



@app.route('/api/readings', methods=['POST'])
def store_reading():
    """Store a new environmental reading"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Required environmental parameters
        required_params = ['co2', 'vocs', 'pm25',
                           'pm10', 'temperature', 'humidity']

        # Validate that all required parameters are present
        for param in required_params:
            if param not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required parameter: {param}'
                }), 400

        # Validate that all values are numeric
        try:
            reading_data = {}
            for param in required_params:
                reading_data[param] = float(data[param])
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'All environmental parameters must be numeric values'
            }), 400

        # Handle optional timestamp (default to current time)
        if 'timestamp' in data and data['timestamp']:
            try:
                # Try to parse the provided timestamp
                timestamp = data['timestamp']
                # Validate ISO format by attempting to parse it
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                reading_data['timestamp'] = timestamp
            except (ValueError, AttributeError):
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid timestamp format. Use ISO format (e.g., 2023-12-01T10:30:00)'
                }), 400
        else:
            # Default to current timestamp
            reading_data['timestamp'] = datetime.now().isoformat()

        # Store the reading in the database
        success = db.insert_reading(reading_data)

        if success:
            return jsonify({
                'status': 'success',
                'message': 'Environmental reading stored successfully',
                'data': {
                    'timestamp': reading_data['timestamp'],
                    'parameters_stored': len(required_params)
                }
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to store reading in database'
            }), 500

    except Exception as e:
        logger.error(f"Error storing reading: {e}", exc_info=True)
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


@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export environmental readings to CSV format"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Validate required fields
        if 'start_date' not in data or 'end_date' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Both start_date and end_date are required'
            }), 400

        try:
            # Parse the datetime strings
            start_date = datetime.fromisoformat(
                data['start_date'].replace('T', ' '))
            end_date = datetime.fromisoformat(
                data['end_date'].replace('T', ' '))
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DDTHH:MM format'
            }), 400

        # Validate date range
        if start_date >= end_date:
            return jsonify({
                'status': 'error',
                'message': 'Start date must be before end date'
            }), 400

        # Limit the date range to prevent excessive data
        date_diff = end_date - start_date
        if date_diff.days > 365:  # Limit to 1 year
            return jsonify({
                'status': 'error',
                'message': 'Date range cannot exceed 1 year'
            }), 400

        # Get readings from database
        readings = db.get_readings_between(start_date, end_date)

        if not readings:
            return jsonify({
                'status': 'error',
                'message': 'No data found for the specified date range'
            }), 404

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write CSV headers
        headers = [
            'Timestamp',
            'CO2 (ppm)',
            'VOCs (ppb)',
            'PM2.5 (μg/m³)',
            'PM10 (μg/m³)',
            'Temperature (°C)',
            'Humidity (%)'
        ]
        writer.writerow(headers)

        # Write data rows
        for reading in readings:
            writer.writerow([
                reading['timestamp'],
                reading['co2'],
                reading['vocs'],
                reading['pm25'],
                reading['pm10'],
                reading['temperature'],
                reading['humidity']
            ])

        # Create response
        output.seek(0)
        csv_data = output.getvalue()
        output.close()

        # Generate filename
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        filename = f'environmental_data_{start_str}_to_{end_str}.csv'

        # Create response with CSV data
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'

        logger.info(
            f"CSV export successful: {len(readings)} records from {start_date} to {end_date}")
        return response

    except Exception as e:
        logger.error(f"Error exporting CSV: {e}", exc_info=True)
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
