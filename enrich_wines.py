"""
Extracts varietal and region from wine names and updates the database.
Run this after parse_emails.py to fill in the varietal/region columns.
"""

import re
import sqlite3
import db as db_module

DB_FILE = "wines.db"

# Ordered longest-first so "Cabernet Sauvignon" matches before "Cabernet"
VARIETALS = [
    # Blends / generics
    "Red Blend", "Red Wine", "White Blend", "White Wine", "Rosé", "Rose", "Rosato",
    # Italian DOC/DOCG (these ARE the varietal+region rolled into one — captured as varietal)
    "Brunello di Montalcino", "Rosso di Montalcino", "Amarone della Valpolicella", "Valpolicella Ripasso",
    "Vino Nobile di Montepulciano", "Morellino di Scansano", "Barolo", "Barbaresco",
    "Barbera d'Asti Superiore", "Barbera d'Asti", "Barbera d'Alba", "Barbera", "Lessona", "Bramaterra",
    "Aglianico del Vulture", "Trebbiano Spoletino", "Roero",
    # French appellations used as varietal
    "Côtes du Rhône Blanc", "Côtes du Rhône", "Cotes du Rhone",
    "Bourgogne", "Mercurey Rouge", "Mercurey", "Saint-Chinian", "Sancerre Rouge", "Sancerre",
    "Saint-Émilion Grand Cru Classé", "Saint-Émilion Grand Cru", "Saint-Émilion",
    "Saint-Georges-Saint-Émilion", "Premier Cru",
    # Spanish
    "Rioja",
    # Austrian
    "Grüner Veltliner", "Gruner Veltliner", "Zweigelt",
    # Italian grapes
    "Sangiovese", "Nebbiolo", "Aglianico", "Pinot Grigio",
    # International
    "Cabernet Sauvignon", "Cabernet Franc", "Pinot Noir", "Chardonnay", "Sauvignon Blanc",
    "Merlot", "Syrah", "Shiraz", "Petite Sirah", "Zinfandel", "Malbec",
    "Semillon", "Grenache", "Tempranillo", "Riesling",
]

# Longest-first for same reason
REGIONS = [
    # California sub-appellations
    "Green Valley of the Russian River Valley", "Spring Mountain District",
    "Moon Mountain District", "Stags Leap District", "Knights Valley",
    "Russian River Valley", "Santa Rita Hills", "Santa Lucia Highlands",
    "Santa Cruz Mountains", "Santa Barbara County", "Anderson Valley", "Edna Valley",
    "Coombsville Napa Valley", "Carneros Napa Valley", "Cienega Valley",
    "Fountaingrove Sonoma County", "Sonoma Coast", "Sonoma County",
    "Dry Creek Valley", "Chalone", "El Dorado", "Lake County",
    "Paso Robles", "Mendocino County", "Mendocino", "North Coast",
    "Napa Valley", "Calistoga", "Oakville", "California",
    # Pacific Northwest
    "Walla Walla Valley", "Willamette Valley",
    # Australia
    "South Australia",
    # Austria
    "Niederösterreich", "Niederosterreich",
    # Italian regions
    "Delle Venezie", "Toscana", "Montalcino", "Montepulciano", "Valpolicella", "Wachau",
    "Umbria", "Tuscany", "Piedmont", "Langhe",
    # French regions
    "Sancerre", "Bordeaux", "Burgundy", "Rhône",
    # Spanish
    "Rioja",
]

# Maps region keywords to State (US) or Country
LOCATION_MAP = {
    # California
    "Green Valley of the Russian River Valley": "California",
    "Spring Mountain District": "California",
    "Moon Mountain District": "California",
    "Stags Leap District": "California",
    "Knights Valley": "California",
    "Russian River Valley": "California",
    "Santa Rita Hills": "California",
    "Sta. Rita Hills": "California",
    "Santa Lucia Highlands": "California",
    "Santa Cruz Mountains": "California",
    "Santa Barbara County": "California",
    "Santa Barbara": "California",
    "Anderson Valley": "California",
    "Edna Valley": "California",
    "Coombsville Napa Valley": "California",
    "Carneros Napa Valley": "California",
    "Cienega Valley": "California",
    "Fountaingrove Sonoma County": "California",
    "Sonoma Coast": "California",
    "Sonoma County": "California",
    "Dry Creek Valley": "California",
    "Chalone": "California",
    "El Dorado": "California",
    "Lake County": "California",
    "Paso Robles": "California",
    "Mendocino County": "California",
    "Mendocino": "California",
    "North Coast": "California",
    "Napa Valley": "California",
    "Calistoga": "California",
    "Oakville": "California",
    "California": "California",
    # Oregon
    "Willamette Valley": "Oregon",
    # Washington
    "Walla Walla Valley": "Washington",
    # Italy
    "Montalcino, Tuscany": "Italy",
    "Barolo, Piedmont": "Italy",
    "Barbaresco, Piedmont": "Italy",
    "Valpolicella, Veneto": "Italy",
    "Montepulciano, Tuscany": "Italy",
    "Scansano, Tuscany": "Italy",
    "Vulture, Basilicata": "Italy",
    "Asti, Piedmont": "Italy",
    "Lessona, Piedmont": "Italy",
    "Bramaterra, Piedmont": "Italy",
    "Roero, Piedmont": "Italy",
    "Tuscany, Italy": "Italy",
    "Toscana": "Italy",
    "Tuscany": "Italy",
    "Delle Venezie": "Italy",
    "Umbria": "Italy",
    "Piedmont": "Italy",
    "Langhe": "Italy",
    "Valpolicella": "Italy",
    # France
    "Sancerre, Loire Valley": "France",
    "Saint-Chinian, Languedoc": "France",
    "Saint-Émilion, Bordeaux": "France",
    "Mercurey, Burgundy": "France",
    "Burgundy, France": "France",
    "Rhône Valley, France": "France",
    "Sancerre": "France",
    "Bordeaux": "France",
    "Burgundy": "France",
    "Rhône": "France",
    # Spain
    "Rioja, Spain": "Spain",
    "Rioja": "Spain",
    # Austria
    "Wachau, Austria": "Austria",
    "Wachau": "Austria",
    "Niederösterreich": "Austria",
    "Niederosterreich": "Austria",
    "Austria": "Austria",
    # Australia
    "South Australia": "Australia",
}


def extract_location(region):
    if not region:
        return None
    # Try full region string first, then keywords within it
    if region in LOCATION_MAP:
        return LOCATION_MAP[region]
    for key, loc in LOCATION_MAP.items():
        if key.lower() in region.lower():
            return loc
    return None


# DOC wines where the varietal name implies the region
DOC_REGION_MAP = {
    "Brunello di Montalcino": "Montalcino, Tuscany",
    "Rosso di Montalcino": "Montalcino, Tuscany",
    "Sancerre Rouge": "Sancerre, Loire Valley",
    "Sancerre": "Sancerre, Loire Valley",
    "Zweigelt": "Austria",
    "Barolo": "Barolo, Piedmont",
    "Barbaresco": "Barbaresco, Piedmont",
    "Amarone della Valpolicella": "Valpolicella, Veneto",
    "Valpolicella Ripasso": "Valpolicella, Veneto",
    "Vino Nobile di Montepulciano": "Montepulciano, Tuscany",
    "Morellino di Scansano": "Scansano, Tuscany",
    "Aglianico del Vulture": "Vulture, Basilicata",
    "Barbera d'Asti Superiore": "Asti, Piedmont",
    "Barbera d'Asti": "Asti, Piedmont",
    "Lessona": "Lessona, Piedmont",
    "Bramaterra": "Bramaterra, Piedmont",
    "Roero": "Roero, Piedmont",
    "Rioja": "Rioja, Spain",
    "Wachau": "Wachau, Austria",
    "Saint-Chinian": "Saint-Chinian, Languedoc",
    "Saint-Émilion Grand Cru Classé": "Saint-Émilion, Bordeaux",
    "Saint-Émilion Grand Cru": "Saint-Émilion, Bordeaux",
    "Saint-Émilion": "Saint-Émilion, Bordeaux",
    "Saint-Georges-Saint-Émilion": "Saint-Émilion, Bordeaux",
    "Mercurey Rouge": "Mercurey, Burgundy",
    "Mercurey": "Mercurey, Burgundy",
    "Bourgogne": "Burgundy, France",
    "Côtes du Rhône Blanc": "Rhône Valley, France",
    "Côtes du Rhône": "Rhône Valley, France",
    "Cotes du Rhone": "Rhône Valley, France",
}


# Known producers and their regions, used as fallback for multi-packs
PRODUCER_REGION_MAP = {
    "Romuald Valot": ("Pinot Noir", "Burgundy, France"),
    "Bibi Graetz": ("Red Blend", "Tuscany, Italy"),
    "Peake Ranch": ("Pinot Noir", "Sta. Rita Hills, Santa Barbara"),
}


def extract_varietal(name):
    # Mystery wines
    if name.lower().startswith("mystery"):
        return "Mystery"

    for v in sorted(VARIETALS, key=len, reverse=True):
        if re.search(re.escape(v), name, re.IGNORECASE):
            return v

    # Producer fallback for multi-packs
    for producer, (varietal, _) in PRODUCER_REGION_MAP.items():
        if producer.lower() in name.lower():
            return varietal

    return None


def extract_region(name, varietal):
    # If the varietal implies a region, use that
    if varietal and varietal in DOC_REGION_MAP:
        return DOC_REGION_MAP[varietal]

    # Producer fallback — only use if it returns a non-None region
    for producer, (_, region) in PRODUCER_REGION_MAP.items():
        if producer.lower() in name.lower() and region:
            return region

    # Otherwise scan for known appellations in the name
    for r in sorted(REGIONS, key=len, reverse=True):
        if re.search(re.escape(r), name, re.IGNORECASE):
            return r

    return None


WINE_TYPES = ("Red", "White", "Rose", "Sparkling", "Dessert", "Fortified", "Orange")

def infer_wine_type(varietal):
    if not varietal:
        return None
    v = varietal.lower()
    if any(x in v for x in ['rosé','rosato','rosado','blush','rosè','rose']):
        return 'Rose'
    if any(x in v for x in ['sparkling','champagne','prosecco','cava','crémant','cremant','sekt','pétillant','petillant','franciacorta','lambrusco']):
        return 'Sparkling'
    if any(x in v for x in ['port','sherry','madeira','marsala','vermouth']):
        return 'Fortified'
    if any(x in v for x in ['sauternes','ice wine','icewine','late harvest','trockenbeerenauslese','beerenauslese','eiswein','tokaj','vin santo']):
        return 'Dessert'
    if any(x in v for x in ['orange wine','skin contact','skin-contact']):
        return 'Orange'
    if any(x in v for x in ['blanc','white wine','chardonnay','riesling','pinot grigio','pinot gris','sauvignon blanc','gewurz','viognier','moscato','grüner','gruner','semillon','trebbiano','vermentino','verdejo','albarino','albariño','torrontes','torrontés','chenin','roussanne','marsanne','grenache blanc','picpoul','assyrtiko','soave','gavi','arneis','trebbiano spoletino']):
        return 'White'
    if any(x in v for x in ['cabernet','merlot','pinot noir','syrah','shiraz','zinfandel','malbec','grenache','sangiovese','nebbiolo','tempranillo','barbera','barolo','barbaresco','brunello','amarone','valpolicella','ripasso','aglianico','petite sirah','mourvedre','petite verdot','carmenere','carmén','zweigelt','blaufränkisch','red blend','red wine','roero','lessona','bramaterra','morellino','rosso','rouge','rioja','bourgogne','mercurey','saint-émilion','saint-emilion','saint-chinian','saint-georges','sancerre rouge','vino nobile','premier cru','côtes du rhône','cotes du rhone']):
        return 'Red'
    return None


SIZE_PATTERNS = [
    (r'\b6[- ]?L\b|\b6000\s*ml\b', 6000),
    (r'\b3[- ]?L\b|\b3000\s*ml\b|double magnum', 3000),
    (r'\bmagnum\b|\b1\.5[- ]?L\b|\b1500\s*ml\b', 1500),
    (r'\b1[- ]?L\b|\b1000\s*ml\b|\b100\s*cl\b', 1000),
    (r'\b375\s*ml\b|\bhalf[- ]bottle\b|\bhalf bottle\b', 375),
    (r'\b187\s*ml\b|\bquarter[- ]bottle\b', 187),
]

def infer_size(wine_name):
    name_lower = wine_name.lower()
    for pattern, ml in SIZE_PATTERNS:
        if re.search(pattern, name_lower):
            return ml
    return 750  # default


def enrich():
    ph = db_module.placeholder
    conn = db_module.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, wine_name, wine_type, size_ml FROM wines")
    wines = cur.fetchall()

    updated = 0
    for wine in wines:
        varietal = extract_varietal(wine["wine_name"])
        region = extract_region(wine["wine_name"], varietal)
        location = extract_location(region)
        wine_type = wine["wine_type"] or infer_wine_type(varietal)
        size_ml = wine["size_ml"] if wine["size_ml"] is not None else infer_size(wine["wine_name"])

        cur.execute(
            f"UPDATE wines SET varietal = {ph}, region = {ph}, location = {ph}, wine_type = {ph}, size_ml = {ph} WHERE id = {ph}",
            (varietal, region, location, wine_type, size_ml, wine["id"])
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"Updated {updated} wines.")

    # Quick summary
    conn = db_module.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT wine_name FROM wines WHERE varietal IS NULL")
    no_varietal = cur.fetchall()
    cur.execute("SELECT wine_name FROM wines WHERE region IS NULL")
    no_region = cur.fetchall()
    conn.close()

    if no_varietal:
        print(f"\n{len(no_varietal)} wines with no varietal matched:")
        for w in no_varietal:
            print(f"  {w['wine_name']}")

    if no_region:
        print(f"\n{len(no_region)} wines with no region matched:")
        for w in no_region:
            print(f"  {w['wine_name']}")


if __name__ == "__main__":
    enrich()
