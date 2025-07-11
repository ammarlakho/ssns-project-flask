# Environmental Monitoring Dashboard

A Flask-based web application for real-time monitoring of environmental parameters with interactive data visualization.

## How To Run

```bash
./setup.sh
./start_server.sh
./start_serial.sh
```

If there are permission issues to run the executable scripts, you can run the following command to make them executable:

```bash
chmod +x setup.sh start_server.sh start_serial.sh
```


## Quick Start

### Option 1: Local Development Setup

1. **Make scripts executable** (first time only):
   ```bash
   chmod +x setup.sh start_server.sh
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
    ./start_server.sh
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


### Database Setup

#### SQLite (Default)
The application uses SQLite by default, which requires no additional setup:

```bash
# Initialize database with sample data
python init_db.py
```


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
| `/api/readings/current` | GET | Current environmental readings | JSON data |
| `/api/readings` | GET | Historical data with time range | JSON data |
| `/api/parameters` | GET | Parameter information and ranges | JSON metadata |
| `/api/stats` | GET | Database statistics | JSON stats |
| `/admin/parameters` | GET | Admin parameters management page | HTML page |
