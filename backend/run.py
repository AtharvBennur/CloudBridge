import os
import sys

from app import create_app

app = create_app()


if __name__ == "__main__":
    debug = app.config.get("DEBUG", False)
    if not debug and not app.config.get("SECRET_KEY"):
        sys.exit(
            "FATAL: SECRET_KEY must be set when running outside of debug mode. "
            "Set it in your .env file or as an environment variable."
        )
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=debug)
