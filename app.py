from gevent import monkey
monkey.patch_all()

from server import create_app, socketio  # noqa: E402

app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
