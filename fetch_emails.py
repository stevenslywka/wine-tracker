"""
Fetches Last Bottle order confirmation emails from Gmail via IMAP.
Run this script to pull emails and save them locally for parsing.
"""

import imaplib
import email
import json
import sqlite3
from datetime import datetime
from email.header import decode_header
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
import db as db_module

DB_FILE = "wines.db"

OUTPUT_FILE = "raw_emails.json"
IMAP_SERVER = "imap.gmail.com"


def decode_str(value):
    if value is None:
        return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def get_body(msg):
    """Extract plain text body, falling back to HTML if needed."""
    plain = None
    html = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if content_type == "text/plain" and plain is None:
                plain = text
            elif content_type == "text/html" and html is None:
                html = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/plain":
                plain = text
            else:
                html = text

    return plain or html or ""


def get_since_date():
    """Return the most recent order_date from the DB as a DD-Mon-YYYY string, or None."""
    try:
        conn = db_module.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT MAX(order_date) FROM wines")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            dt = datetime.strptime(row[0], "%Y-%m-%d")
            return dt.strftime("%d-%b-%Y")
    except Exception:
        pass
    return None


def fetch_emails(since_date=None):
    if since_date is None:
        since_date = get_since_date()

    print("Connecting to Gmail via IMAP...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    if since_date:
        print(f"Searching for Last Bottle emails since {since_date}...")
        status, data = mail.search(None, f'(FROM "noreply@lastbottlewines.com" SINCE {since_date})')
    else:
        print("Searching for all Last Bottle emails...")
        status, data = mail.search(None, 'FROM', '"noreply@lastbottlewines.com"')

    if status != "OK":
        print("Search failed.")
        return

    message_ids = data[0].split()
    print(f"Found {len(message_ids)} emails.")

    emails = []
    for i, msg_id in enumerate(message_ids):
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        emails.append({
            "id": msg_id.decode(),
            "date": decode_str(msg.get("Date", "")),
            "subject": decode_str(msg.get("Subject", "")),
            "from": decode_str(msg.get("From", "")),
            "body": get_body(msg),
        })

        if (i + 1) % 10 == 0:
            print(f"  Fetched {i + 1}/{len(message_ids)}...")

    mail.logout()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Saved {len(emails)} emails to {OUTPUT_FILE}")


if __name__ == "__main__":
    fetch_emails()
