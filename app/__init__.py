#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Flask application factory for mangadex-dl-wui-vibed."""

import base64
from pathlib import Path

import minify_html
from flask import Flask, Response

from app.config import Config

_ASSETS_DIR = Path(__file__).parent.parent / "assets"


def _load_b64(path: Path) -> str:
    data = path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    favicon_b64 = _load_b64(_ASSETS_DIR / "logo" / "32x32.png")
    logo_b64 = _load_b64(_ASSETS_DIR / "logo" / "128x128.png")

    @app.context_processor
    def inject_images() -> dict[str, str]:
        return {"favicon_b64": favicon_b64, "logo_b64": logo_b64}

    @app.after_request
    def minify_response(response: Response) -> Response:
        if response.content_type.startswith("text/html"):
            response.set_data(
                minify_html.minify(
                    response.get_data(as_text=True),
                    minify_js=True,
                    minify_css=True,
                )
            )
        return response

    from app.routes import bp

    app.register_blueprint(bp)

    return app
