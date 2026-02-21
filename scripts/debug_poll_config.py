#!/usr/bin/env python3
"""Debug script: inspect AppConfig injection in rendered index HTML."""

from unittest.mock import patch

from app import create_app

app = create_app()
app.config["TESTING"] = True

with app.test_client() as c:
    with patch("app.routes.Config") as m:
        m.POLL_INTERVAL_SECONDS = 5
        r = c.get("/")
        html = r.data.decode()

        idx = html.find("AppConfig")
        if idx >= 0:
            print("Found AppConfig at", idx, ":", repr(html[idx : idx + 80]))
        else:
            print("AppConfig NOT found")

        idx2 = html.find("pollIntervalMs")
        print("pollIntervalMs at:", idx2)
        if idx2 >= 0:
            print("  context:", repr(html[idx2 : idx2 + 40]))

        idx3 = html.find("5000")
        print("5000 at:", idx3)
