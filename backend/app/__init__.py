from flask import Flask

def create_app():
    app = Flask(__name__)
    from .routes.events import events_bp
    from .routes.predictions import predictions_bp

    app.register_blueprint(events_bp, url_prefix="/api/events")
    app.register_blueprint(predictions_bp, url_prefix="/api/predictions")

    return app