import pandas as pd

# --- 1. Config ---
csv_file = "SB_publication_PMC.csv"
link_column_name = "Link"

# --- 2. Load CSV ---
try:
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    print(f"Error: The file '{csv_file}' was not found.")
    exit()
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit()

if link_column_name not in df.columns:
    print(f"Error: Column '{link_column_name}' not found in CSV.")
    print("Available columns:", list(df.columns))
    exit()

# --- 3. Identify Duplicates ---
links = df[link_column_name].dropna()
duplicates = links[links.duplicated(keep=False)]

if duplicates.empty:
    print("✅ No repeated links found.")
else:
    print(f"⚠️ Found {duplicates.nunique()} unique repeated links.")
    print(f"Total repeated entries: {len(duplicates)}")

    # --- 4. Show repeated links and counts ---
    dup_counts = duplicates.value_counts()
    for link, count in dup_counts.items():
        print(f"{link} → {count} times")

    # Optional: save to file
    dup_counts.to_csv("repeated_links.csv", header=["count"])
    print("\nSaved repeated links to 'repeated_links.csv'")
