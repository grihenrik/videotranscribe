"""
Temporary Flask app to serve our static content while we work on the FastAPI integration.
"""
from flask import Flask, send_from_directory, redirect

app = Flask(__name__)

@app.route('/')
def index():
    """Serve the index.html page"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    try:
        return send_from_directory('static', path)
    except:
        return 'File not found', 404

@app.route('/api')
def api_docs():
    """Redirect to API docs"""
    return redirect('/docs')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)