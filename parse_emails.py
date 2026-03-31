"""
Parses Last Bottle order confirmation emails into structured wine purchase records.
Reads raw_emails.json, saves to wines.db and parsed_wines.json.
"""

import json
import re
import sqlite3
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
import db as db_module

RAW_EMAILS_FILE = "raw_emails.json"
PARSED_FILE = "parsed_wines.json"
DB_FILE = "wines.db"


def init_db():
    conn = db_module.get_connection()
    ph = db_module.placeholder
    if db_module.is_postgres():
        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS wines (
                id SERIAL PRIMARY KEY,
                email_id TEXT UNIQUE,
                order_date TEXT,
                retailer TEXT,
                wine_name TEXT,
                vintage INTEGER,
                varietal TEXT,
                region TEXT,
                quantity INTEGER,
                unit_price REAL,
                total_price REAL,
                order_number TEXT,
                notes TEXT,
                status TEXT DEFAULT 'cellar'
            )
        """)
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT UNIQUE,
                order_date TEXT,
                retailer TEXT,
                wine_name TEXT,
                vintage INTEGER,
                varietal TEXT,
                region TEXT,
                quantity INTEGER,
                unit_price REAL,
                total_price REAL,
                order_number TEXT,
                notes TEXT,
                status TEXT DEFAULT 'cellar'
            )
        """)
    conn.commit()
    return conn


def extract_vintage(name):
    """Pull a 4-digit year from the wine name."""
    match = re.search(r'\b(19|20)\d{2}\b', name)
    return int(match.group()) if match else None


def parse_price(text):
    """Convert '$39.00' -> 39.0"""
    text = text.strip().replace(',', '')
    match = re.search(r'[\d.]+', text)
    return float(match.group()) if match else None


def is_new_format(body):
    """New-format emails contain product URLs."""
    return 'lastbottlewines.com/products/' in body


def parse_new_format(email):
    """Parse newer LBW email format (plain text with product URLs and two prices)."""
    body = email['body']
    results = []

    order_number = None
    match = re.search(r'Order No\. #(\S+)', body)
    if match:
        order_number = match.group(1)
    if not order_number:
        match = re.search(r'Order #(\S+)', email.get('subject', ''))
        if match:
            order_number = match.group(1)

    order_date = email.get('date', '')
    try:
        order_date = parsedate_to_datetime(order_date).strftime('%Y-%m-%d')
    except Exception:
        pass

    # Find all product URLs, then extract wine name from preceding lines
    url_pattern = re.compile(
        r'\(\s*(https://lastbottlewines\.com/products/([a-z0-9\-]+)[^\s)]*)',
        re.IGNORECASE
    )

    for m in url_pattern.finditer(body):
        product_url = m.group(1).strip()

        # Get the lines immediately before the URL (up to 3 lines back)
        before = body[:m.start()]
        preceding_lines = [l.strip() for l in before.split('\n') if l.strip()][-3:]

        # Combine lines that together contain a 4-digit year
        wine_name = None
        for i in range(len(preceding_lines) - 1, -1, -1):
            candidate = ' '.join(preceding_lines[i:])
            if re.search(r'\b(19|20)\d{2}\b', candidate):
                # If this candidate is very short it's likely a wrapped line — go back one more
                if len(candidate) < 25 and i > 0:
                    candidate = ' '.join(preceding_lines[i - 1:])
                wine_name = candidate
                break

        if not wine_name:
            continue
        # Strip any leftover URL fragments from the name
        wine_name = re.sub(r'\(\s*https?://\S+\s*\)', '', wine_name).strip()

        # Skip if it looks like boilerplate rather than a wine name
        if any(skip in wine_name.lower() for skip in ['order no', 'items ordered', 'view order']):
            continue

        # Find qty and prices in the text after this match
        after = body[m.end():]

        qty = 1
        qty_match = re.search(r'x\s*(\d+)', after[:300])
        if qty_match:
            qty = int(qty_match.group(1))

        # Find two prices: retail (first) then LB price (second)
        prices = re.findall(r'\$[\d,]+\.\d{2}', after[:400])
        retail_price = parse_price(prices[0]) if len(prices) >= 1 else None
        lb_price = parse_price(prices[1]) if len(prices) >= 2 else retail_price

        # If only one price found, it's the LB price
        if len(prices) == 1:
            lb_price = retail_price
            retail_price = None

        vintage = extract_vintage(wine_name)

        results.append({
            'email_id': email['id'],
            'order_date': order_date,
            'retailer': 'Last Bottle',
            'wine_name': wine_name,
            'vintage': vintage,
            'varietal': None,
            'region': None,
            'quantity': qty,
            'unit_price': lb_price,
            'total_price': lb_price * qty if lb_price and qty else lb_price,
            'retail_price': retail_price,
            'product_url': product_url,
            'order_number': order_number,
        })

    return results


def parse_old_format(email):
    """Parse older LBW HTML email format."""
    soup = BeautifulSoup(email['body'], 'html.parser')
    results = []

    order_number = None
    for td in soup.find_all('td'):
        text = td.get_text(strip=True)
        if text == 'ORDER #':
            next_row = td.find_parent('tr')
            if next_row:
                next_row = next_row.find_next_sibling('tr')
                if next_row:
                    next_td = next_row.find('td')
                    if next_td:
                        order_number = next_td.get_text(strip=True)
            break
    if not order_number:
        match = re.search(r'Order #(\S+)', email.get('subject', ''))
        if match:
            order_number = match.group(1)

    order_date = email.get('date', '')
    try:
        order_date = parsedate_to_datetime(order_date).strftime('%Y-%m-%d')
    except Exception:
        match = re.search(r'(\d{2}/\d{2}/\d{4})', email['body'])
        if match:
            order_date = match.group(1)

    for td in soup.find_all('td'):
        style = td.get('style', '')
        if 'ED1C24' not in style.upper():
            continue
        wine_name = td.get_text(strip=True)
        if not wine_name or len(wine_name) < 5:
            continue
        if re.match(r'^[A-Z0-9]{5,12}$', wine_name):
            continue
        if any(skip in wine_name.lower() for skip in ['invite', 'friend', 'help@', 'tell all']):
            continue

        row = td.find_parent('tr')
        if not row:
            continue
        cells = [c for c in row.find_all('td') if c.get_text(strip=True)]

        qty = None
        price = None
        if len(cells) >= 3:
            price_text = cells[-1].get_text(strip=True)
            qty_text = cells[-2].get_text(strip=True)
            if price_text.startswith('$'):
                price = parse_price(price_text)
            if qty_text and qty_text.isdigit():
                qty = int(qty_text)

        vintage = extract_vintage(wine_name)
        results.append({
            'email_id': email['id'],
            'order_date': order_date,
            'retailer': 'Last Bottle',
            'wine_name': wine_name,
            'vintage': vintage,
            'varietal': None,
            'region': None,
            'quantity': qty,
            'unit_price': price,
            'total_price': price * qty if price and qty else price,
            'retail_price': None,
            'product_url': None,
            'order_number': order_number,
        })

    return results


def parse_order_email(email):
    if is_new_format(email['body']):
        return parse_new_format(email)
    return parse_old_format(email)


def parse_all_emails():
    with open(RAW_EMAILS_FILE, "r", encoding="utf-8") as f:
        emails = json.load(f)

    # Only parse order confirmations, skip shipment notices
    order_emails = [
        e for e in emails
        if 'shipment' not in e.get('subject', '').lower()
    ]

    conn = init_db()
    ph = db_module.placeholder
    all_wines = []
    errors = 0

    print(f"Parsing {len(order_emails)} order emails (skipping shipment notices)...")

    for i, email in enumerate(order_emails):
        try:
            wines = parse_order_email(email)

            for wine in wines:
                try:
                    cur = conn.cursor()
                    if db_module.is_postgres():
                        cur.execute(f"""
                            INSERT INTO wines
                            (email_id, order_date, retailer, wine_name, vintage, varietal,
                             region, quantity, unit_price, total_price, order_number,
                             retail_price, product_url)
                            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                            ON CONFLICT (email_id) DO NOTHING
                        """, (
                            wine['email_id'], wine['order_date'], wine['retailer'],
                            wine['wine_name'], wine['vintage'], wine['varietal'],
                            wine['region'], wine['quantity'], wine['unit_price'],
                            wine['total_price'], wine['order_number'],
                            wine.get('retail_price'), wine.get('product_url'),
                        ))
                    else:
                        cur.execute("""
                            INSERT OR IGNORE INTO wines
                            (email_id, order_date, retailer, wine_name, vintage, varietal,
                             region, quantity, unit_price, total_price, order_number,
                             retail_price, product_url)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            wine['email_id'], wine['order_date'], wine['retailer'],
                            wine['wine_name'], wine['vintage'], wine['varietal'],
                            wine['region'], wine['quantity'], wine['unit_price'],
                            wine['total_price'], wine['order_number'],
                            wine.get('retail_price'), wine.get('product_url'),
                        ))
                    conn.commit()
                except Exception as e:
                    print(f"  DB error: {e}")

                all_wines.append(wine)

        except Exception as e:
            print(f"  [{i+1}] Error: {type(e).__name__}: {e}")
            errors += 1

    with open(PARSED_FILE, "w", encoding="utf-8") as f:
        json.dump(all_wines, f, indent=2, ensure_ascii=False)

    conn.close()

    print(f"\nDone.")
    print(f"  Wines extracted: {len(all_wines)}")
    print(f"  Emails with errors: {errors}")
    print(f"  Saved to {DB_FILE} and {PARSED_FILE}")


if __name__ == "__main__":
    parse_all_emails()
