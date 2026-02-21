#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Flask application factory for mangadex-dl-wui-vibed."""

import minify_html
from flask import Flask, Response

from app.config import Config


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__, static_folder="../assets", static_url_path="/assets")
    app.config.from_object(Config)

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
