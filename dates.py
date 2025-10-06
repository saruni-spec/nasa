import json
import os
import re
from datetime import datetime
from typing import Optional
import psycopg2
from dotenv import load_dotenv


load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("PGDATABASE", "neondb"),
    "user": os.getenv("PGUSER", "neondb_owner"),
    "password": os.getenv("PGPASSWORD", ""),
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", 5432),
    "sslmode": os.getenv("PGSSLMODE", "require"),
}
INPUT_JSON = "merged_articles.json"


def normalize_date(date_str: str) -> Optional[datetime.date]:
    """
    Parses various date string formats into a datetime.date object.
    Includes the fix for 'YYYY Mon DD' format.
    """
    if not date_str or date_str.strip() == "":
        return None

    # Strip potential leading/trailing whitespace and ensure the string is usable
    date_str = date_str.strip()

    # List of date formats to try, in order of specificity
    formats_to_try = [
        # 1. YYYY-MM-DD (e.g., 2021-01-01)
        "%Y-%m-%d",
        # 2. YYYY Mon DD (e.g., 2024 Mar 25) <-- THIS IS THE REQUIRED FIX
        "%Y %b %d",
        # 3. Mon DD, YYYY (e.g., Mar 25, 2024) - often a fallback
        "%b %d, %Y",
        # 4. YYYY Mon (e.g., 2013 Jan)
        "%Y %b",
        # 5. Just YYYY
        "%Y",
    ]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


def run_date_update_script():
    """
    Loads JSON data, re-parses dates, and updates the articles table directly.
    """
    print("Starting date update script...")

    try:
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            articles = json.load(f)
        print(f"Loaded {len(articles)} articles from {INPUT_JSON}.")
    except FileNotFoundError:
        print(f"ERROR: Input file {INPUT_JSON} not found. Exiting.")
        return
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {INPUT_JSON}. Exiting.")
        return

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor()
    except Exception as e:
        print(f"ERROR: Could not connect to the database. Check DB_CONFIG. Error: {e}")
        return

    update_count = 0
    total_count = len(articles)

    for i, article in enumerate(articles):
        pmcid = article.get("pmcid")

        if not pmcid:
            continue

        # Get the original date string from the article's metadata
        original_date_str = article.get("metadata", {}).get("publication_date")

        if original_date_str:
            # Normalize the date using the corrected function
            new_date = normalize_date(original_date_str)

            if new_date:

                try:
                    cursor.execute(
                        """
                        UPDATE articles 
                        SET publication_date = %s
                        WHERE pmcid = %s
                        AND (publication_date IS NULL OR publication_date != %s)
                        """,
                        (new_date, pmcid, new_date),
                    )

                    if cursor.rowcount > 0:
                        update_count += 1

                except Exception as e:
                    print(f"ERROR updating {pmcid} with date {new_date}: {e}")
                    conn.rollback()

            if (i + 1) % 100 == 0:
                print(
                    f"Processed {i + 1}/{total_count}. Updates so far: {update_count}"
                )

    try:
        conn.commit()
        print("\n" + "=" * 50)
        print("UPDATE COMPLETE")
        print(f"Successfully processed: {total_count} articles")
        print(f"Total records updated: {update_count}")
        print("=" * 50)
    except Exception as e:
        print(f"FATAL ERROR during commit: {e}")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    run_date_update_script()
