import os
import collections
from bs4 import BeautifulSoup

# Directory with your scraped HTML files
INPUT_DIR = "scraped_html_files"

# Collectors
meta_counter = collections.Counter()
div_class_counter = collections.Counter()
div_id_counter = collections.Counter()
header_counter = collections.Counter()


def inspect_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "lxml")

        # Meta tags
        for m in soup.find_all("meta"):
            if m.get("name"):
                meta_counter[m["name"].strip().lower()] += 1

        # Div classes and ids
        for d in soup.find_all("div"):
            if d.get("class"):
                for c in d.get("class"):
                    div_class_counter[c.strip().lower()] += 1
            if d.get("id"):
                div_id_counter[d["id"].strip().lower()] += 1

        # Headers
        for h in soup.find_all(["h1", "h2", "h3", "h4"]):
            txt = h.get_text(" ", strip=True).lower()
            if txt:
                header_counter[txt] += 1

    except Exception as e:
        print(f"❌ Error processing {path}: {e}")


def main():
    files = [
        os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR) if f.endswith(".html")
    ]
    print(f"Found {len(files)} HTML files to inspect...\n")

    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Inspecting {f}")
        inspect_file(f)

    print("\n--- Summary of structures across all files ---\n")

    print("Top META tags:")
    for name, count in meta_counter.most_common(20):
        print(f"  {name}: {count}")

    print("\nTop DIV classes:")
    for name, count in div_class_counter.most_common(20):
        print(f"  {name}: {count}")

    print("\nTop DIV ids:")
    for name, count in div_id_counter.most_common(20):
        print(f"  {name}: {count}")

    print("\nTop Headers (h1–h4 text):")
    for name, count in header_counter.most_common(20):
        print(f"  {name[:60]}: {count}")


if __name__ == "__main__":
    main()
