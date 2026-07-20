from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "tongliao4a4-dev"

    socketio.init_app(app)

    from .routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    from .routes import ws  # 注册 WebSocket 事件处理器

    from .store import start_cleanup_thread
    start_cleanup_thread()

    return app
