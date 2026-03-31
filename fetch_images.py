"""
Fetches wine bottle images from Last Bottle product pages.
Run this after parse_emails.py to populate image_url for new-format wines.
"""

import sqlite3
import urllib.request
import re
import time
import db as db_module

DB_FILE = "wines.db"


def fetch_image_url(product_url):
    """Scrape the og:image or first product image from a Last Bottle product page."""
    try:
        req = urllib.request.Request(
            product_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; wine-tracker/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Try og:image first (most reliable)
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']', html)
        if match:
            return match.group(1)

        # Fallback: look for CDN product image
        match = re.search(r'(https://cdn\.shopify\.com/s/files/[^"\'?\s]+\.(jpg|png|webp))', html)
        if match:
            return match.group(1)

    except Exception as e:
        print(f"    Failed to fetch {product_url}: {e}")

    return None


def _fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _og_image(html):
    match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']', html)
    if not match:
        match = re.search(r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']', html)
    return match.group(1) if match else None


def _search_wine_searcher(wine_name):
    import urllib.parse
    query = urllib.parse.quote_plus(wine_name)
    html = _fetch_html(f"https://www.wine-searcher.com/find/{query}")
    # Try og:image on search results page first
    img = _og_image(html)
    if img and "wine-searcher" in img:
        return img
    # Follow first product link
    match = re.search(r'href="(https://www\.wine-searcher\.com/wine/[^"]+)"', html)
    if not match:
        match = re.search(r'href="(/wine/[a-z0-9\-+/]+)"', html)
        if match:
            match = type('m', (), {'group': lambda self, n: "https://www.wine-searcher.com" + match.group(1)})()
    if match:
        product_html = _fetch_html(match.group(1))
        img = _og_image(product_html)
        if img:
            return img
    return None


def _search_wine_enthusiast(wine_name):
    import urllib.parse
    query = urllib.parse.quote_plus(wine_name)
    html = _fetch_html(f"https://www.winemag.com/?s={query}&drink_type=wine")
    # Find first review link
    match = re.search(r'href="(https://www\.winemag\.com/buying-guide/[^"]+)"', html)
    if match:
        product_html = _fetch_html(match.group(1))
        img = _og_image(product_html)
        if img:
            return img
    return None


def search_and_fetch_image(wine_name):
    """Search Wine Searcher then Wine Enthusiast for a bottle image."""
    for fn, label in [(_search_wine_searcher, "Wine Searcher"), (_search_wine_enthusiast, "Wine Enthusiast")]:
        try:
            img = fn(wine_name)
            if img:
                print(f"  Found image via {label}.")
                return img
        except Exception as e:
            print(f"  {label} search failed for '{wine_name}': {e}")
    print(f"  No image found for '{wine_name}'.")
    return None


def fetch_all_images():
    ph = db_module.get_placeholder()
    conn = db_module.get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, wine_name, product_url
        FROM wines
        WHERE product_url IS NOT NULL AND image_url IS NULL
    """)
    wines = cur.fetchall()

    if not wines:
        print("No wines with product URLs missing images.")
        conn.close()
        return

    print(f"Fetching images for {len(wines)} wines...")
    updated = 0

    for wine in wines:
        print(f"  {wine['wine_name'][:60]}...")
        image_url = fetch_image_url(wine['product_url'])
        if image_url:
            cur2 = conn.cursor()
            cur2.execute(f"UPDATE wines SET image_url = {ph} WHERE id = {ph}", (image_url, wine['id']))
            conn.commit()
            updated += 1
            print(f"    Got image.")
        else:
            print(f"    No image found.")
        time.sleep(0.5)  # Be polite to their server

    conn.close()
    print(f"\nDone. Updated {updated}/{len(wines)} wines with images.")


if __name__ == "__main__":
    fetch_all_images()
