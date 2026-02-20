#!/usr/bin/env python3

#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Check what the minified cache page HTML output actually contains."""
import re
import sys
from unittest.mock import patch

sys.path.insert(0, ".")

from app import create_app

app = create_app()
with app.test_client() as c:
    with patch("app.routes.list_cached_mangas") as mock:
        mock.return_value = [
            {
                "url": "https://mangadex.org/title/abc",
                "name": "Test",
                "sanitized_name": "Test",
                "cache_path": "/cache/Test",
                "download_date": "2026-01-01T00:00:00+00:00",
                "files": ["ch1.cbz"],
            }
        ]
        r = c.get("/cache")
        html = r.get_data(as_text=True)

        print("=== status-badge context ===")
        m = re.search(r"class.{0,40}status-badge.{0,40}", html)
        print(m.group() if m else "NOT FOUND")
        print()

        print("=== Class attribute forms ===")
        for cls in [
            "task-card",
            "task-header",
            "file-list",
            "cache-series-name",
            "navbar",
            "disclaimer",
        ]:
            quoted = f'class="{cls}"' in html
            unquoted = f"class={cls}" in html
            print(f"  {cls}: quoted={quoted}, unquoted={unquoted}")
