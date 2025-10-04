from bs4 import BeautifulSoup
import os


def extract_article_data(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    data = {}

    # --- Title ---
    # Often inside <meta name="citation_title"> or <title>
    meta_title = soup.find("meta", {"name": "citation_title"})
    if meta_title:
        data["title"] = meta_title.get("content", "").strip()
    else:
        if soup.title:
            data["title"] = soup.title.get_text(strip=True)

    # --- Authors ---
    # Usually multiple <meta name="citation_author">
    authors = [
        m.get("content", "").strip()
        for m in soup.find_all("meta", {"name": "citation_author"})
    ]
    data["authors"] = authors

    # --- Abstract ---
    # Look for h2/h3 with text "Abstract" and capture following <p>
    abstract_text = ""
    abstract_header = soup.find(
        ["h2", "h3"], string=lambda s: s and "abstract" in s.lower()
    )
    if abstract_header:
        # grab all sibling <p> until next header
        p_tags = []
        for sib in abstract_header.find_next_siblings():
            if sib.name in ["h2", "h3"]:
                break
            if sib.name == "p":
                p_tags.append(sib.get_text(" ", strip=True))
        abstract_text = " ".join(p_tags)
    data["abstract"] = abstract_text

    return data


if __name__ == "__main__":
    file_path = "scraped_html_files/PMC6371294.html"  # test on one
    if os.path.exists(file_path):
        article = extract_article_data(file_path)
        print(article)
    else:
        print("❌ File not found")
