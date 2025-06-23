# Flask Basic Repository

A simple Flask web application with a modern UI and basic API endpoints.


## Quick Start

1. **Make scripts executable** (first time only):
   ```bash
   chmod +x setup.sh start.sh
   ```

2. **Run setup script** (creates virtual environment and installs dependencies):
   ```bash
   ./setup.sh
   ```

3. **Start the application**:
   ```bash
   ./start.sh
   ```

4. **Access the application**:
   - Open your browser and go to: `http://localhost:8000`
   - The API endpoints are available at:
     - `http://localhost:8000/api/health`
     - `http://localhost:8000/api/hello`

## Project Structure

```
ssns-project-flask/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   └── index.html     # Main page template
├── test_app.py        # Basic tests
├── setup.sh           # Setup script (creates venv & installs deps)
├── start.sh           # Startup script (runs the app)
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## API Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/` | GET | Main page | HTML page |
| `/api/health` | GET | Health check | JSON status |
| `/api/hello` | GET | Hello message | JSON message |

### Example API Responses

**Health Check** (`/api/health`):
```json
{
  "status": "healthy",
  "message": "Flask app is running!"
}
```

**Hello API** (`/api/hello`):
```json
{
  "message": "Hello, World!"
}
```

## Development

### Running in Development Mode

The application runs in debug mode by default, which provides:
- Automatic reloading when code changes
- Detailed error messages
- Debug toolbar (if installed)

### Environment Variables

You can set the following environment variables:

- `SECRET_KEY`: Secret key for Flask sessions (defaults to a development key)

### Adding New Routes

To add new routes, edit `app.py`:

```python
@app.route('/your-new-route')
def your_new_function():
    return jsonify({'message': 'Your response'})
```

### Running Tests

```bash
# Activate virtual environment first
source venv/bin/activate

# Run tests
python test_app.py
```

## Deployment

For production deployment:

1. Set a proper `SECRET_KEY` environment variable
2. Disable debug mode
3. Use a production WSGI server like Gunicorn
4. Set up proper logging and monitoring

### Example with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```