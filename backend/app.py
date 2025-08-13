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
    from src.api.predict_match import ns as predict_match_ns
    PREDICT_MATCH_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ predict_match not available: {e}")
    PREDICT_MATCH_AVAILABLE = False


try:
    from src.api.match_predictions_direct import ns as match_predictions_direct_ns
    MATCH_PREDICTIONS_DIRECT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ match_predictions_direct not available: {e}")
    MATCH_PREDICTIONS_DIRECT_AVAILABLE = False

# Try to import the new enhanced match analysis
try:
    from src.api.match_analysis import ns as match_analysis_ns
    MATCH_ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ match_analysis not available: {e}")
    MATCH_ANALYSIS_AVAILABLE = False

try:
    from src.api.ai_review import ns as ai_review_ns
    AI_REVIEW_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ai_review not available: {e}")
    AI_REVIEW_AVAILABLE = False

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
              description="Enhanced API for armwrestling predictions and match analysis",
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
    # register conditionally
    if PREDICT_MATCH_AVAILABLE:
        api.add_namespace(predict_match_ns, path="/predict-match")
        print("✅ Registered /predict-match endpoint")

    # Register optional namespaces if available
    if MATCH_PREDICTIONS_AVAILABLE:
        api.add_namespace(match_predictions_ns, path="/match-predictions")
        print("✅ Registered /match-predictions endpoint")
    
    if MATCH_PREDICTIONS_DIRECT_AVAILABLE:
        api.add_namespace(match_predictions_direct_ns, path="/match-predictions-direct")
        print("✅ Registered /match-predictions-direct endpoint")
    
    if MATCH_ANALYSIS_AVAILABLE:
        api.add_namespace(match_analysis_ns, path="/match-analysis")
        print("✅ Registered /match-analysis endpoint (Enhanced)")

    if AI_REVIEW_AVAILABLE:
        api.add_namespace(ai_review_ns, path="/ai-review")
        print("✅ Registered /ai-review endpoint")

    
    @app.get("/media/<path:filename>")
    def media(filename):
        base = Path(__file__).resolve().parents[1] / "media"
        return send_from_directory(base, filename)
    
    # Health check endpoint
    @app.route("/health")
    def health_check():
        endpoints_status = {
            "core_endpoints": True,
            "match_predictions": MATCH_PREDICTIONS_AVAILABLE,
            "match_predictions_direct": MATCH_PREDICTIONS_DIRECT_AVAILABLE,
            "enhanced_match_analysis": MATCH_ANALYSIS_AVAILABLE
        }
        
        return {
            "status": "healthy",
            "endpoints": endpoints_status,
            "available_routes": [
                "/athletes",
                "/predict", 
                "/events",
                "/match-predictions" if MATCH_PREDICTIONS_AVAILABLE else None,
                "/match-predictions-direct" if MATCH_PREDICTIONS_DIRECT_AVAILABLE else None,
                "/match-analysis" if MATCH_ANALYSIS_AVAILABLE else None
            ]
        }
    
    return app

if __name__ == "__main__":
    print("🚀 Starting Enhanced Flask app...")
    print(f"📁 Current directory: {Path.cwd()}")
    
    try:
        app = create_app()
        print("✅ App created successfully")
        print("🌐 Starting server on http://localhost:5000")
        print("📚 Swagger docs available at http://localhost:5000/swagger/")
        print("🔍 Health check available at http://localhost:5000/health")
        
        # Print available endpoints
        available_endpoints = []
        if MATCH_PREDICTIONS_AVAILABLE:
            available_endpoints.append("✅ /match-predictions - Standard prediction search")
        if MATCH_PREDICTIONS_DIRECT_AVAILABLE:
            available_endpoints.append("✅ /match-predictions-direct - Direct pipeline access")
        if MATCH_ANALYSIS_AVAILABLE:
            available_endpoints.append("✅ /match-analysis - Enhanced analysis with explanations")
        
        if available_endpoints:
            print("\n📊 Available prediction endpoints:")
            for endpoint in available_endpoints:
                print(f"   {endpoint}")
        
        app.run(debug=True, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"❌ Failed to start app: {e}")
        print("🔧 Try running with just core endpoints first")