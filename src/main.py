from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Config
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "app.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="dev"  # replace in prod
    )

    # Init extensions
    db.init_app(app)
    CORS(app)

    # Import models
    from src.models.user import User

    # Create tables
    with app.app_context():
        db.create_all()

    # Register routes
    from src.routes.video import video_bp
    app.register_blueprint(video_bp, url_prefix="/api/video")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)
