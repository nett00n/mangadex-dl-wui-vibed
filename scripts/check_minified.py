#!/usr/bin/env python3

#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Check what the minified HTML output actually contains."""
import re
import sys

sys.path.insert(0, ".")

from app import create_app

app = create_app()
with app.test_client() as c:
    r = c.get("/")
    html = r.get_data(as_text=True)

    print("=== HTML start ===")
    print(html[:300])
    print()

    print("=== Attribute quotes ===")
    print("Has class=navbar:", "class=navbar" in html)
    print('Has class="navbar":', 'class="navbar"' in html)
    print("Has id=download-form:", "id=download-form" in html)
    print('Has id="download-form":', 'id="download-form"' in html)
    print()

    print("=== Script block ===")
    idx = html.find("<script>")
    end = html.find("</script>", idx)
    script = html[idx : end + 9]
    print(f"Script length: {len(script)} chars")
    consts = re.findall(r"const \w+", script)
    print("Const declarations:", consts[:20])
    print()

    print("=== Data URIs ===")
    print("Has data:image/png;base64:", "data:image/png;base64," in html)
    print()

    print("=== Whitespace ===")
    print('Has excessive whitespace (\\n    \\n):', "\n    \n" in html)
