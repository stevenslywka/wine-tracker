"""
Wine Tracker web app. Run with: python app.py
Then open http://localhost:5000 in your browser.
"""

import sqlite3
import os
import uuid
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
DB_FILE = "wines.db"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


def save_upload(file):
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return f"/static/uploads/{filename}"

WINE_TYPES = ("Red", "White", "Rose", "Sparkling", "Dessert", "Fortified", "Orange")

def infer_wine_type(varietal):
    if not varietal:
        return None
    v = varietal.lower()
    if any(x in v for x in ['rosé','rosato','rosado','blush','rosè']):
        return 'Rose'
    if any(x in v for x in ['sparkling','champagne','prosecco','cava','crémant','cremant','sekt','pétillant','petillant','franciacorta','lambrusco']):
        return 'Sparkling'
    if any(x in v for x in ['port','sherry','madeira','marsala','vermouth']):
        return 'Fortified'
    if any(x in v for x in ['sauternes','ice wine','icewine','late harvest','trockenbeerenauslese','beerenauslese','eiswein','tokaj','vin santo']):
        return 'Dessert'
    if any(x in v for x in ['orange wine','skin contact','skin-contact']):
        return 'Orange'
    if any(x in v for x in ['blanc','white wine','chardonnay','riesling','pinot grigio','pinot gris','sauvignon blanc','gewurz','viognier','moscato','grüner','gruner','semillon','trebbiano','vermentino','verdejo','albarino','albariño','torrontes','torrontés','chenin','roussanne','marsanne','grenache blanc','picpoul','assyrtiko','soave','gavi','arneis']):
        return 'White'
    if any(x in v for x in ['cabernet','merlot','pinot noir','syrah','shiraz','zinfandel','malbec','grenache','sangiovese','nebbiolo','tempranillo','barbera','barolo','barbaresco','brunello','amarone','valpolicella','ripasso','aglianico','petite sirah','mourvedre','petite verdot','carmenere','carmén','zweigelt','blaufränkisch','red blend','red wine','roero','lessona','bramaterra','morellino','rosso','rouge','rioja','bourgogne','mercurey','saint-émilion','saint-emilion','saint-chinian','saint-georges','sancerre rouge','vino nobile','premier cru']):
        return 'Red'
    return None


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    conn = get_db()
    search = request.args.get("q", "")
    status_filter = request.args.get("status", "")
    varietal_filter = request.args.get("varietal", "")
    region_filter = request.args.get("region", "")
    location_filter = request.args.get("location", "")
    vintage_min = request.args.get("vintage_min", "")
    vintage_max = request.args.get("vintage_max", "")
    price_min = request.args.get("price_min", "")
    price_max = request.args.get("price_max", "")
    sort = request.args.get("sort", "order_date")
    order = request.args.get("order", "desc")

    allowed_sorts = {"order_date", "wine_name", "vintage", "unit_price", "retail_price", "quantity", "color_code", "region", "location", "varietal", "my_rating", "wine_type", "size_ml"}
    if sort not in allowed_sorts:
        sort = "order_date"
    if order not in {"asc", "desc"}:
        order = "desc"

    query = "SELECT * FROM wines WHERE 1=1"
    params = []

    if search:
        query += " AND (wine_name LIKE ? OR varietal LIKE ? OR region LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if varietal_filter:
        query += " AND varietal = ?"
        params.append(varietal_filter)
    if region_filter:
        query += " AND region = ?"
        params.append(region_filter)
    if location_filter:
        query += " AND location = ?"
        params.append(location_filter)
    if vintage_min:
        query += " AND vintage >= ?"
        params.append(int(vintage_min))
    if vintage_max:
        query += " AND vintage <= ?"
        params.append(int(vintage_max))
    if price_min:
        query += " AND unit_price >= ?"
        params.append(float(price_min))
    if price_max:
        query += " AND unit_price <= ?"
        params.append(float(price_max))
    color_filter = request.args.get("color_code", "")
    if color_filter:
        query += " AND color_code = ?"
        params.append(color_filter)

    query += f" ORDER BY {sort} {order}"

    wines = conn.execute(query, params).fetchall()

    stats = conn.execute("""
        SELECT
            SUM(quantity) as total_bottles,
            COUNT(DISTINCT wine_name) as unique_wines,
            SUM(total_price) as total_spent,
            SUM(CASE WHEN status='cellar' THEN quantity ELSE 0 END) as in_cellar
        FROM wines
    """).fetchone()

    # Populate filter dropdowns with distinct values
    varietals = [r[0] for r in conn.execute(
        "SELECT DISTINCT varietal FROM wines WHERE varietal IS NOT NULL ORDER BY varietal"
    ).fetchall()]
    regions = [r[0] for r in conn.execute(
        "SELECT DISTINCT region FROM wines WHERE region IS NOT NULL ORDER BY region"
    ).fetchall()]
    locations = [r[0] for r in conn.execute(
        "SELECT DISTINCT location FROM wines WHERE location IS NOT NULL ORDER BY location"
    ).fetchall()]
    vintages = [r[0] for r in conn.execute(
        "SELECT DISTINCT vintage FROM wines WHERE vintage IS NOT NULL ORDER BY vintage DESC"
    ).fetchall()]

    conn.close()
    return render_template("index.html", wines=wines, stats=stats,
                           search=search, status_filter=status_filter,
                           varietal_filter=varietal_filter, region_filter=region_filter,
                           location_filter=location_filter, color_filter=color_filter,
                           vintage_min=vintage_min, vintage_max=vintage_max,
                           price_min=price_min, price_max=price_max,
                           sort=sort, order=order,
                           varietals=varietals, regions=regions,
                           locations=locations, vintages=vintages)


@app.route("/wine/<int:wine_id>")
def wine_detail(wine_id):
    conn = get_db()
    wine = conn.execute("SELECT * FROM wines WHERE id = ?", (wine_id,)).fetchone()
    conn.close()
    if not wine:
        return "Wine not found", 404
    return render_template("detail.html", wine=wine)


@app.route("/wines/bulk-status", methods=["POST"])
def bulk_update_status():
    ids = request.form.getlist("ids")
    new_status = request.form.get("status")
    if new_status not in ("apt", "house", "not_shipped", "drank"):
        return ("", 400)
    conn = get_db()
    conn.executemany("UPDATE wines SET status = ? WHERE id = ?", [(new_status, id_) for id_ in ids])
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/status", methods=["POST"])
def update_status(wine_id):
    new_status = request.form.get("status")
    if new_status in ("apt", "house", "not_shipped", "drank"):
        conn = get_db()
        conn.execute("UPDATE wines SET status = ? WHERE id = ?", (new_status, wine_id))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for("index"))


@app.route("/wine/<int:wine_id>/color", methods=["POST"])
def update_color(wine_id):
    color = request.form.get("color_code", "")
    if color in ("Red", "Blue", "Orange", "Yellow", "Green", ""):
        conn = get_db()
        conn.execute("UPDATE wines SET color_code = ? WHERE id = ?", (color or None, wine_id))
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for("index"))


BOTTLE_SIZES = (187, 375, 750, 1000, 1500, 3000, 6000)

@app.route("/wine/<int:wine_id>/size", methods=["POST"])
def update_size(wine_id):
    raw = request.form.get("size_ml", "").strip()
    if raw == "":
        size = None
    else:
        try:
            size = int(raw)
            if size not in BOTTLE_SIZES:
                return ("", 400)
        except ValueError:
            return ("", 400)
    conn = get_db()
    conn.execute("UPDATE wines SET size_ml = ? WHERE id = ?", (size, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/type", methods=["POST"])
def update_type(wine_id):
    wine_type = request.form.get("wine_type", "")
    if wine_type not in WINE_TYPES and wine_type != "":
        return ("", 400)
    conn = get_db()
    conn.execute("UPDATE wines SET wine_type = ? WHERE id = ?", (wine_type or None, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/rating", methods=["POST"])
def update_rating(wine_id):
    raw = request.form.get("my_rating", "").strip()
    if raw == "":
        rating = None
    else:
        try:
            rating = round(float(raw), 1)
            if not (0.0 <= rating <= 5.0):
                return ("", 400)
        except ValueError:
            return ("", 400)
    conn = get_db()
    conn.execute("UPDATE wines SET my_rating = ? WHERE id = ?", (rating, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/delete", methods=["POST"])
def delete_wine(wine_id):
    conn = get_db()
    conn.execute("DELETE FROM wines WHERE id = ?", (wine_id,))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/retailer", methods=["POST"])
def update_retailer(wine_id):
    retailer = request.form.get("retailer", "").strip() or None
    conn = get_db()
    conn.execute("UPDATE wines SET retailer = ? WHERE id = ?", (retailer, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/<int:wine_id>/notes", methods=["POST"])
def update_notes(wine_id):
    notes = request.form.get("notes", "")
    conn = get_db()
    conn.execute("UPDATE wines SET notes = ? WHERE id = ?", (notes, wine_id))
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/wine/add", methods=["POST"])
def add_wine():
    from enrich_wines import extract_varietal, extract_region, extract_location, infer_wine_type, infer_size
    from fetch_images import search_and_fetch_image

    wine_name = request.form.get("wine_name", "").strip()
    if not wine_name:
        return redirect(url_for("index"))

    raw_vintage    = request.form.get("vintage", "").strip()
    raw_price      = request.form.get("unit_price", "").strip()
    raw_quantity   = request.form.get("quantity", "1").strip()
    notes          = request.form.get("notes", "").strip() or None
    retailer       = request.form.get("retailer", "").strip() or None
    raw_order_date = request.form.get("order_date", "").strip()

    try:    vintage  = int(raw_vintage)  if raw_vintage  else None
    except ValueError: vintage = None
    try:    unit_price = float(raw_price) if raw_price else None
    except ValueError: unit_price = None
    try:    quantity = max(1, int(raw_quantity)) if raw_quantity else 1
    except ValueError: quantity = 1

    order_date  = raw_order_date if raw_order_date else date.today().isoformat()
    total_price = round(unit_price * quantity, 2) if unit_price else None

    varietal  = extract_varietal(wine_name)
    region    = extract_region(wine_name, varietal)
    location  = extract_location(region)
    wine_type = infer_wine_type(varietal)
    size_ml   = infer_size(wine_name)

    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO wines
            (wine_name, vintage, unit_price, total_price, quantity, notes,
             varietal, region, location, wine_type, size_ml,
             retailer, order_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'cellar')
    """, (wine_name, vintage, unit_price, total_price, quantity, notes,
          varietal, region, location, wine_type, size_ml,
          retailer, order_date))
    wine_id = cursor.lastrowid
    conn.commit()
    conn.close()

    uploaded = request.files.get("image")
    if uploaded and uploaded.filename:
        image_url = save_upload(uploaded)
    else:
        image_url = search_and_fetch_image(wine_name)
    if image_url:
        conn = get_db()
        conn.execute("UPDATE wines SET image_url = ? WHERE id = ?", (image_url, wine_id))
        conn.commit()
        conn.close()

    return redirect(url_for("index"))


@app.route("/refresh", methods=["POST"])
def refresh():
    from fetch_emails import fetch_emails
    from parse_emails import parse_all_emails
    from enrich_wines import enrich
    from fetch_images import fetch_all_images
    fetch_emails()
    parse_all_emails()
    enrich()
    fetch_all_images()
    return redirect(url_for("index"))


@app.route("/api/wines")
def api_wines():
    conn = get_db()
    wines = conn.execute("SELECT * FROM wines ORDER BY order_date DESC").fetchall()
    conn.close()
    return jsonify([dict(w) for w in wines])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
