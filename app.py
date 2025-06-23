from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'dev-secret-key-change-in-production')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask app is running!'})


@app.route('/api/hello')
def hello():
    return jsonify({'message': 'Hello, World!'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
