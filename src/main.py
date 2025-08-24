from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# Initialize SQLAlchemy (db object imported by models)
db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance folder exists (where SQLite DB will live)
    os.makedirs(app.instance_path, exist_ok=True)

    # Config
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "app.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="dev"  # ⚠️ Replace in production
    )

    # Init extensions
    db.init_app(app)
    CORS(app)

    # Import models
    from src.models.user import User

    # Create tables if not exist
    with app.app_context():
        db.create_all()

    # Register blueprints (routes)
    from src.routes.video import video_bp
    app.register_blueprint(video_bp, url_prefix="/api/video")

    @app.route("/")
    def index():
        return {"message": "Video Enhancer API running ✅"}

    return app


if __name__ == "__main__":
    app = create_app()
    # ⚠️ use_reloader=False to avoid signal issues on Python 3.13
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
