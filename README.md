# Environmental Monitoring Dashboard

A Flask-based web application for real-time monitoring of environmental parameters with interactive data visualization.

## Features

- **Real-time Environmental Monitoring**: Track CO2, VOCs, PM2.5, PM10, temperature, and humidity
- **Interactive Dashboard**: Modern, responsive web interface with real-time updates
- **Historical Data Visualization**: Chart.js-powered graphs with customizable time ranges
- **Status Indicators**: Color-coded status indicators for each parameter
- **RESTful API**: Complete API for data access and integration
- **Auto-refresh**: Automatic data updates every 30 seconds
- **Database Storage**: SQLite database
- **Modular Architecture**: Clean separation of concerns with database abstraction layer
- **Docker Support**: Containerized deployment with data persistence

## Monitored Parameters

| Parameter | Unit | Description | Normal Range | Dangerous Level |
|-----------|------|-------------|--------------|-----------------|
| Carbon Dioxide (CO2) | ppm | Concentration of carbon dioxide in the air | 400-1000 | >1000 |
| Volatile Organic Compounds (VOCs) | ppb | Concentration of volatile organic compounds | 0-500 | >500 |
| PM2.5 | μg/m³ | Fine particulate matter (≤2.5μm) | 0-12 | >35 |
| PM10 | μg/m³ | Coarse particulate matter (≤10μm) | 0-54 | >150 |
| Temperature | °C | Ambient air temperature | 18-25 | <10 or >30 |
| Humidity | % | Relative humidity of the air | 30-60 | <20 or >80 |

## Quick Start

### Option 1: Local Development Setup

1. **Make scripts executable** (first time only):
   ```bash
   chmod +x setup.sh start.sh
   ```

2. **Run setup script** (creates virtual environment and installs dependencies):
   ```bash
   ./setup.sh
   ```

3. **Initialize the database** (first time only):
   ```bash
   python init_db.py
   ```

4. **Start the application**:
   ```bash
   ./start.sh
   ```

5. **Access the dashboard**:
   - Open your browser and go to: `http://localhost:8000`
   - View real-time environmental data and historical trends

### Option 2: Docker Deployment (Recommended for Production)

#### Prerequisites
- Docker installed and running on your system
- Git (to clone the repository)

#### Quick Docker Start

1. **Make the script executable**:
   ```bash
   chmod +x run-docker.sh
   ```

2. **Start the application**:
   ```bash
   ./run-docker.sh start
   ```

3. **Access the application**:
   - Open your browser and go to: `http://localhost:8000`

#### Manual Docker Commands

1. **Build the Docker image**:
   ```bash
   docker build -t ssns-flask-app .
   ```

2. **Create data directories**:
   ```bash
   mkdir -p data logs
   ```

3. **Run the container**:
   ```bash
   docker run -d \
     --name ssns-flask-app \
     -p 8000:8000 \
     -v "$(pwd)/data:/app/data" \
     -v "$(pwd)/logs:/app/logs" \
     -e DB_PATH=/app/data/environmental_data.db \
     ssns-flask-app
   ```

#### Docker Management Commands

**Using the script**:
- `./run-docker.sh start` - Build and start the application
- `./run-docker.sh stop` - Stop the application
- `./run-docker.sh restart` - Restart the application
- `./run-docker.sh logs` - View application logs
- `./run-docker.sh status` - Show application status
- `./run-docker.sh cleanup` - Remove container and image
- `./run-docker.sh build` - Build the Docker image only
- `./run-docker.sh run` - Run the container (assumes image is built)

**Manual Docker commands**:
- Stop the container: `docker stop ssns-flask-app`
- Remove the container: `docker rm ssns-flask-app`
- View logs: `docker logs -f ssns-flask-app`
- View container status: `docker ps -a --filter name=ssns-flask-app`

#### Docker Environment Variables

You can customize the application by setting environment variables:

- `DB_PATH`: Path to the SQLite database file (default: `/app/data/environmental_data.db`)
- `SECRET_KEY`: Flask secret key for session management

Example:
```bash
docker run -d \
  --name ssns-flask-app \
  -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  -e DB_PATH=/app/data/environmental_data.db \
  -e SECRET_KEY=your-secret-key-here \
  ssns-flask-app
```

#### Docker Data Persistence

The application uses SQLite database stored in the `data/` directory. This directory is mounted as a volume to ensure data persistence between container restarts.

#### Docker Troubleshooting

1. **Port already in use**: If port 8000 is already in use, change the port mapping:
   ```bash
   docker run -d --name ssns-flask-app -p 8001:8000 ssns-flask-app
   ```

2. **Permission issues**: Make sure the script is executable:
   ```bash
   chmod +x run-docker.sh
   ```

3. **Container won't start**: Check the logs:
   ```bash
   docker logs ssns-flask-app
   ```

4. **Database issues**: The database will be automatically initialized when the container starts for the first time.

## Database

The application uses a modular database architecture that makes it easy to switch between different database systems.

### Database Architecture

- **Abstract Interface**: `DatabaseInterface` defines the contract for all database implementations
- **SQLite Implementation**: Current implementation using SQLite for simplicity
- **Factory Pattern**: `DatabaseFactory` creates appropriate database instances
- **Configuration Management**: Environment-based configuration for different database types

### Database Setup

#### SQLite (Default)
The application uses SQLite by default, which requires no additional setup:

```bash
# Initialize database with sample data
python init_db.py
```

### Database Operations

The database layer provides these operations:
- `insert_reading()`: Add new environmental readings
- `get_latest_reading()`: Get most recent reading
- `get_readings_since()`: Get readings from last N hours
- `get_readings_between()`: Get readings between timestamps
- `get_reading_count()`: Get total number of readings
- `clear_old_readings()`: Clean up old data
- `populate_sample_data()`: Add sample data for testing

### Database Schema

```sql
CREATE TABLE environmental_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    co2 REAL NOT NULL,
    vocs REAL NOT NULL,
    pm25 REAL NOT NULL,
    pm10 REAL NOT NULL,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON environmental_readings(timestamp);
```

## Project Structure

```
ssns-project-flask/
├── app.py              # Main Flask application
├── init_db.py          # Database initialization script
├── requirements.txt    # Python dependencies
├── database/           # Database layer
│   ├── __init__.py     # Package initialization
│   ├── config.py       # Database configuration
│   ├── interface.py    # Abstract database interface
│   ├── sqlite_db.py    # SQLite implementation
│   └── factory.py      # Database factory
├── templates/          # HTML templates
│   ├── index.html     # Environmental monitoring dashboard
│   ├── 404.html       # 404 error page
│   ├── 500.html       # 500 error page
│   └── admin_parameters.html # Admin parameters page
├── test_app.py        # Comprehensive test suite
├── setup.sh           # Setup script (creates venv & installs deps)
├── start.sh           # Startup script (runs the app)
├── run-docker.sh      # Docker management script
├── Dockerfile         # Docker container definition
├── data/              # Data directory (created by Docker)
├── logs/              # Logs directory (created by Docker)
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## API Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/` | GET | Environmental monitoring dashboard | HTML page |
| `/api/health` | GET | Health check with database status | JSON status |
| `/api/current` | GET | Current environmental readings | JSON data |
| `/api/historical` | GET | Historical data with time range | JSON data |
| `/api/parameters` | GET | Parameter information and ranges | JSON metadata |
| `/api/stats` | GET | Database statistics | JSON stats |
| `/admin/parameters` | GET | Admin parameters management page | HTML page |

### Example API Responses

**Health Check** (`/api/health`):
```json
{
  "status": "healthy",
  "message": "Environmental monitoring system is running!",
  "database": {
    "type": "sqlite",
    "readings_count": 1440
  }
}
```

**Current Readings** (`/api/current`):
```json
{
  "status": "success",
  "data": {
    "timestamp": "2024-01-15T10:30:00",
    "co2": 450.25,
    "vocs": 125.50,
    "pm25": 8.75,
    "pm10": 25.30,
    "temperature": 22.5,
    "humidity": 45.2
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

**Database Stats** (`/api/stats`):
```json
{
  "status": "success",
  "stats": {
    "total_readings": 1440,
    "latest_reading_timestamp": "2024-01-15T10:30:00",
    "database_type": "sqlite"
  }
}
```

**Historical Data** (`/api/historical?hours=24`):
```json
{
  "status": "success",
  "data": [
    {
      "timestamp": "2024-01-14T10:30:00",
      "co2": 445.20,
      "vocs": 120.30,
      "pm25": 8.50,
      "pm10": 24.80,
      "temperature": 22.3,
      "humidity": 44.8
    }
    // ... more data points
  ],
  "hours": 24
}
```

**Parameters Info** (`/api/parameters`):
```json
{
  "parameters": {
    "co2": {
      "name": "Carbon Dioxide",
      "unit": "ppm",
      "description": "Concentration of carbon dioxide in the air",
      "normal_range": "400-1000",
      "dangerous_level": ">1000"
    }
    // ... other parameters
  }
}
```

## Dashboard Features

### Real-time Monitoring
- Live display of current environmental readings
- Color-coded status indicators (Good/Moderate/Poor)
- Auto-refresh every 30 seconds
- Responsive design for mobile and desktop

### Historical Data Visualization
- Interactive line charts using Chart.js
- Multiple time range options (1 hour to 1 week)
- Multiple Y-axes for different parameter scales
- Hover tooltips with detailed information

### User Interface
- Modern, clean design with gradient background
- Card-based layout for easy reading
- Smooth animations and transitions
- Mobile-responsive design

## Development

### Running in Development Mode

The application runs in debug mode by default, which provides:
- Automatic reloading when code changes
- Detailed error messages
- Debug toolbar (if installed)

### Environment Variables

You can set the following environment variables:

- `SECRET_KEY`: Secret key for Flask sessions (defaults to a development key)

### Sample Data

The application currently uses generated sample data for demonstration. In production, you would:
1. Replace the sample data generation with real sensor data
2. Implement database storage for historical data
3. Add authentication and user management
4. Implement real-time data streaming

### Adding New Parameters

To add new environmental parameters:

1. Update the `generate_sample_data()` function in `app.py`
2. Add parameter information to the `/api/parameters` endpoint
3. Update the dashboard template to display the new parameter
4. Add corresponding tests in `test_app.py`

### Running Tests

```bash
# Activate virtual environment first
source venv/bin/activate

# Run tests
python test_app.py
```

The test suite includes:
- API endpoint functionality tests
- Data generation and retrieval tests
- Error handling tests
- Parameter validation tests

## Deployment

For production deployment:

1. Set a proper `SECRET_KEY` environment variable
2. Disable debug mode
3. Use a production WSGI server like Gunicorn
4. Set up proper logging and monitoring
5. Implement real sensor data integration
6. Add database for persistent data storage

### Example with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Future Enhancements

- Database integration for persistent data storage
- Real sensor data integration
- User authentication and authorization
- Alert system for dangerous levels
- Data export functionality
- Mobile app integration
- Advanced analytics and reporting
- Multi-location monitoring support