from flask import Flask, send_from_directory
from flask_restx import Api
from flask_cors import CORS
from pathlib import Path


from src.api.athletes import ns as athletes_ns
from src.api.prediction import ns as prediction_ns
from src.api.events import ns as events_ns  

def create_app():
    app = Flask(__name__)
    CORS(app)
    api = Api(app, title="Armwrestling Prediction API", version="1.0", doc="/swagger/")
    api.add_namespace(athletes_ns, path="/athletes")
    api.add_namespace(prediction_ns, path="/predict")
    api.add_namespace(events_ns, path="/events")

    @app.get("/media/<path:filename>")
    def media(filename):
        base = Path(__file__).resolve().parents[1] / "media"  # project/media
        return send_from_directory(base, filename)
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
