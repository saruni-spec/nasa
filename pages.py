import pandas as pd
import requests
import os
from urllib.parse import urlparse

# Define the name of your CSV file
csv_file = "SB_publication_PMC.csv"
# Define the directory where the HTML files will be saved
output_directory = "scraped_html_files"
# Define the column containing the links
link_column_name = "Link"

#  Headers to Mimic a Browser ---links
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# --- 1. Create Output Directory ---
if not os.path.exists(output_directory):
    os.makedirs(output_directory)
    print(f"Created output directory: {output_directory}")

# --- 2. Read the CSV File ---
try:
    # Use the file content fetcher to get the content of the CSV

    # the file is present.
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    print(f"Error: The file '{csv_file}' was not found.")
    exit()
except Exception as e:
    print(f"An error occurred while reading the CSV: {e}")
    exit()

if link_column_name not in df.columns:
    print(f"Error: Could not find a column named '{link_column_name}' in the CSV.")
    print(f"Available columns are: {list(df.columns)}")
    exit()

print(f"Total rows in CSV: {len(df)}")
print(f"Non-null links: {df[link_column_name].notna().sum()}")
print(f"Unique links: {df[link_column_name].dropna().nunique()}")


links = df[link_column_name].dropna().unique()
print(f"Found {len(links)} unique links to process.")

# --- 3. Scrape and Save HTML for Each Link ---
for i, url in enumerate(links):
    print(f"\nProcessing link {i+1}/{len(links)}: {url}")

    try:
        # Use requests to get the content, passing the headers
        response = requests.get(url, headers=headers, timeout=15)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Get the HTML content
        html_content = response.text

        # --- Filename Logic (uses the PMC ID from the URL) ---
        parsed_url = urlparse(url)
        path_segments = [seg for seg in parsed_url.path.split("/") if seg]

        if path_segments:
            # The PMC ID is usually the last segment
            file_base_name = path_segments[-1]
        else:
            file_base_name = f"page_{i}"

        # Create a safe filename
        filename = f"{file_base_name}.html"
        full_path = os.path.join(output_directory, filename)

        # Save the HTML content to a file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Successfully saved HTML to: {full_path}")

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error for {url}: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Connection Error for {url}: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error for {url}: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred for {url}: {err}")
    except Exception as e:
        print(f"An unexpected error occurred for {url}: {e}")

print("\n--- Scraping Attempt Complete ---")
print(f"Check the '{output_directory}' directory for successful downloads.")
