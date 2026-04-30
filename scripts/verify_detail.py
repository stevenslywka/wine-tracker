"""Run lightweight Wine Detail verification checks.

This script is intentionally local-dev friendly. It can run with Codex's
bundled Python by adding the app's virtualenv packages to sys.path.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
BUNDLED_NODE = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node.exe"


def ok(message: str) -> None:
    print(f"OK  {message}")


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def add_venv_packages() -> None:
    sys.path.insert(0, str(ROOT))
    if VENV_PACKAGES.exists():
        sys.path.insert(0, str(VENV_PACKAGES))


def compile_python() -> None:
    for filename in ("app.py", "db.py"):
        py_compile.compile(str(ROOT / filename), doraise=True)
    ok("Python syntax for app.py and db.py")


def import_app_modules():
    os.chdir(ROOT)
    add_venv_packages()
    import db  # noqa: PLC0415
    import app as wine_app  # noqa: PLC0415

    return db, wine_app


def run_migration(db) -> None:
    db.migrate()
    ok("db.migrate() completed")


def first_wine_and_user(db):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id FROM wines ORDER BY id LIMIT 1")
    wine = cur.fetchone()
    if not wine:
        conn.close()
        fail("No wines found in local database")
    cur.execute("SELECT username FROM users WHERE id = ?", (wine["user_id"],))
    user = cur.fetchone()
    conn.close()
    if not user:
        fail("No user found for first wine")
    return wine, user


def render_detail(db, wine_app) -> str:
    wine, user = first_wine_and_user(db)
    client = wine_app.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = wine["user_id"]
        session["username"] = user["username"]
    response = client.get(f"/wine/{wine['id']}")
    if response.status_code != 200:
        fail(f"/wine/{wine['id']} returned HTTP {response.status_code}")
    html = response.get_data(as_text=True)
    for marker in ("Bottle Ledger", "addBottleModal", "locationEditModal", "historyEditModal"):
        if marker not in html:
            fail(f"Rendered detail page missing {marker}")
    ok(f"Rendered /wine/{wine['id']} with Bottle Ledger markup")
    return html


def check_inline_script(html: str) -> None:
    node = BUNDLED_NODE if BUNDLED_NODE.exists() else None
    if node is None:
        ok("Skipped inline JavaScript syntax check; bundled Node was not found")
        return

    scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
    if not scripts:
        fail("No inline script found in rendered detail page")
    script = scripts[-1]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
        handle.write("new Function(")
        handle.write(repr(script))
        handle.write(");\n")
        temp_path = handle.name
    try:
        result = subprocess.run([str(node), temp_path], capture_output=True, text=True, timeout=20)
    finally:
        Path(temp_path).unlink(missing_ok=True)
    if result.returncode != 0:
        fail(f"Inline JavaScript syntax check failed: {result.stderr.strip()}")
    ok("Inline JavaScript syntax")


def main() -> None:
    compile_python()
    db, wine_app = import_app_modules()
    run_migration(db)
    html = render_detail(db, wine_app)
    check_inline_script(html)
    ok("Wine Detail verification complete")


if __name__ == "__main__":
    main()
