from flask import Flask, send_from_directory
from flask_restx import Api
from flask_cors import CORS
from pathlib import Path

# Safe imports with error handling
from src.api.athletes import ns as athletes_ns
from src.api.prediction import ns as prediction_ns
from src.api.events import ns as events_ns

# Try to import existing namespaces
try:
    from src.api.match_predictions import ns as match_predictions_ns
    MATCH_PREDICTIONS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ match_predictions not available: {e}")
    MATCH_PREDICTIONS_AVAILABLE = False

try:
    from src.api.match_predictions_direct import ns as match_predictions_direct_ns
    MATCH_PREDICTIONS_DIRECT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ match_predictions_direct not available: {e}")
    MATCH_PREDICTIONS_DIRECT_AVAILABLE = False

def create_app():
    app = Flask(__name__)
    
    # FIXED: Use ONLY Flask-CORS, remove duplicate header setting
    CORS(app, 
         origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept"],
         supports_credentials=True)
    
    # Configure Flask-RESTX
    api = Api(app, 
              title="Armwrestling Prediction API", 
              version="1.0", 
              doc="/swagger/",
              authorizations={
                  'apikey': {
                      'type': 'apiKey',
                      'in': 'header',
                      'name': 'X-API-Key'
                  }
              })
    
    # Register core namespaces (always available)
    api.add_namespace(athletes_ns, path="/athletes")
    api.add_namespace(prediction_ns, path="/predict")
    api.add_namespace(events_ns, path="/events")
    
    # Register optional namespaces if available
    if MATCH_PREDICTIONS_AVAILABLE:
        api.add_namespace(match_predictions_ns, path="/match-predictions")
        print("✅ Registered /match-predictions endpoint")
    
    if MATCH_PREDICTIONS_DIRECT_AVAILABLE:
        api.add_namespace(match_predictions_direct_ns, path="/match-predictions-direct")
        print("✅ Registered /match-predictions-direct endpoint")

    @app.get("/media/<path:filename>")
    def media(filename):
        base = Path(__file__).resolve().parents[1] / "media"
        return send_from_directory(base, filename)
    
    # REMOVED: Duplicate CORS header setting that was causing the issue
    # The flask-cors extension handles this automatically
    
    return app

if __name__ == "__main__":
    print("🚀 Starting Flask app...")
    print(f"📁 Current directory: {Path.cwd()}")
    
    try:
        app = create_app()
        print("✅ App created successfully")
        print("🌐 Starting server on http://localhost:5000")
        print("📚 Swagger docs available at http://localhost:5000/swagger/")
        app.run(debug=True, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"❌ Failed to start app: {e}")
        print("🔧 Try running with just core endpoints first")