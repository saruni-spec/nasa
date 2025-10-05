"""
Enhanced NASA Bioscience Article Extractor
Extracts comprehensive metadata from PMC HTML files
"""

import re
from bs4 import BeautifulSoup
import os, json, pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import spacy
from collections import Counter


try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run:")
    print("python -m spacy download en_core_web_sm")
    nlp = None


INPUT_DIR = "scraped_html_files"
OUTPUT_JSON = "articles_detailed.json"
OUTPUT_CSV = "articles_detailed.csv"
OUTPUT_METADATA_CSV = "articles_metadata.csv"

# Map variations of section headers to canonical names
SECTION_MAP = {
    "abstract": "abstract",
    "introduction": "introduction",
    "materials and methods": "materials_and_methods",
    "methods": "materials_and_methods",
    "materials & methods": "materials_and_methods",
    "results": "results",
    "results and discussion": "results",
    "discussion": "discussion",
    "conclusion": "conclusions",
    "conclusions": "conclusions",
    "concluding remarks": "conclusions",
    "acknowledgments": "acknowledgments",
    "acknowledgements": "acknowledgments",
    "supplementary materials": "supplementary_materials",
    "supplementary material": "supplementary_materials",
    "supporting information": "supplementary_materials",
    "author contributions": "author_contributions",
    "funding": "funding",
    "funding statement": "funding",
    "financial support": "funding",
    "conflicts of interest": "conflicts_of_interest",
    "competing interests": "conflicts_of_interest",
    "conflict of interest": "conflicts_of_interest",
    "references": "references",
    "footnotes": "footnotes",
    "data availability statement": "data_availability",
    "data availability": "data_availability",
    "informed consent statement": "informed_consent",
    "institutional review board statement": "irb_statement",
    "ethics statement": "irb_statement",
}


def normalize_section_name(header_text: str) -> str:
    """Normalize headers like '1. Introduction' -> 'introduction'"""
    text = header_text.lower().strip()
    # Remove leading numbers, dots, and special chars
    text = re.sub(r"^[0-9\.\s\-–—]+", "", text)
    # Remove trailing colons
    text = text.rstrip(":")
    return SECTION_MAP.get(text, text.replace(" ", "_"))


def extract_publication_date(soup: BeautifulSoup) -> Optional[str]:
    """Extract publication date from meta tags"""
    # Try various meta tag formats
    date_fields = [
        ("meta", {"name": "citation_publication_date"}),
        ("meta", {"name": "citation_date"}),
        ("meta", {"name": "DC.Date"}),
        ("meta", {"property": "article:published_time"}),
    ]

    for tag, attrs in date_fields:
        meta = soup.find(tag, attrs)
        if meta and meta.get("content"):
            date_str = meta.get("content", "").strip()
            # Try to parse and standardize
            try:
                # Handle various formats: YYYY/MM/DD, YYYY-MM-DD, etc.
                for fmt in ["%Y/%m/%d", "%Y-%m-%d", "%Y", "%d %B %Y", "%B %d, %Y"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
                # If no format matches, return as is
                return date_str
            except:
                return date_str

    return None


def extract_doi(soup: BeautifulSoup) -> Optional[str]:
    """Extract DOI from meta tags"""
    doi_meta = soup.find("meta", {"name": "citation_doi"})
    if doi_meta:
        doi = doi_meta.get("content", "").strip()
        # Clean DOI (remove https://doi.org/ prefix if present)
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return doi
    return None


def extract_journal_info(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract journal name, volume, issue, pages"""
    info = {"journal": None, "volume": None, "issue": None, "pages": None, "issn": None}

    # Journal name
    journal_meta = soup.find("meta", {"name": "citation_journal_title"})
    if journal_meta:
        info["journal"] = journal_meta.get("content", "").strip()

    # Volume
    volume_meta = soup.find("meta", {"name": "citation_volume"})
    if volume_meta:
        info["volume"] = volume_meta.get("content", "").strip()

    # Issue
    issue_meta = soup.find("meta", {"name": "citation_issue"})
    if issue_meta:
        info["issue"] = issue_meta.get("content", "").strip()

    # Pages
    firstpage = soup.find("meta", {"name": "citation_firstpage"})
    lastpage = soup.find("meta", {"name": "citation_lastpage"})
    if firstpage and lastpage:
        info["pages"] = f"{firstpage.get('content', '')}-{lastpage.get('content', '')}"
    elif firstpage:
        info["pages"] = firstpage.get("content", "")

    # ISSN
    issn_meta = soup.find("meta", {"name": "citation_issn"})
    if issn_meta:
        info["issn"] = issn_meta.get("content", "").strip()

    return info


# function to replace extract_keywords_from_abstract
def extract_keywords_with_spacy(
    sections: Dict[str, str], max_keywords: int = 15
) -> List[str]:
    """
    Extracts keywords from abstract using spaCy's NLP capabilities.
    Focuses on noun chunks and important nouns.
    """
    if not nlp:
        return []  # Return empty if spaCy model is not loaded

    abstract_text = sections.get("abstract", "")
    if not abstract_text or len(abstract_text) < 50:
        return []

    # Process the text with spaCy
    doc = nlp(abstract_text)

    keywords = []

    # 1. Extract noun chunks (multi-word keywords like "oxidative stress")
    # We clean them up to remove stop words or punctuation at the edges.
    for chunk in doc.noun_chunks:
        # A noun chunk can be just a single noun or a phrase.
        # We check its length and make sure it's not a stop word.
        clean_chunk = chunk.text.lower().strip()
        if len(clean_chunk) > 4 and chunk.root.is_stop is False:
            keywords.append(clean_chunk)

    # 2. Extract important individual nouns (for terms spaCy might miss in chunks)
    # We look for nouns that are not stop words or punctuation.
    for token in doc:
        if (
            not token.is_stop
            and not token.is_punct
            and token.pos_ == "NOUN"  # Part Of Speech is NOUN
            and len(token.text) > 4
        ):
            keywords.append(token.lemma_.lower())  # Use the base form of the word

    # 3. Count frequencies and return the most common keywords
    if not keywords:
        return []

    keyword_counts = Counter(keywords)
    # Return the most common keywords, de-duplicated
    return [kw for kw, count in keyword_counts.most_common(max_keywords)]


def extract_keywords_from_meta(soup: BeautifulSoup) -> List[str]:
    """Extract author-provided keywords from meta tags AND body sections"""
    keywords = []

    # METHOD 1: Try meta tags first (in case they exist)
    keyword_meta = soup.find_all("meta", {"name": "citation_keywords"})
    for meta in keyword_meta:
        kw = meta.get("content", "").strip()
        if kw:
            if ";" in kw:
                keywords.extend([k.strip() for k in kw.split(";")])
            elif "," in kw:
                keywords.extend([k.strip() for k in kw.split(",")])
            else:
                keywords.append(kw)

    # METHOD 2: Search for keyword sections in the body
    # Look for sections with ID or class containing "keyword" or "kwd"
    keyword_sections = soup.find_all(
        ["section", "div", "p"], id=re.compile(r"(keyword|kwd)", re.I)
    )

    if not keyword_sections:
        keyword_sections = soup.find_all(
            ["section", "div", "p"], class_=re.compile(r"(keyword|kwd)", re.I)
        )

    for section in keyword_sections:
        text = section.get_text()
        # Remove common prefixes
        text = re.sub(r"^(keywords?|key\s*words?)[\s:;\-–—]*", "", text, flags=re.I)

        # Try splitting by various delimiters
        if ";" in text:
            kws = [k.strip() for k in text.split(";")]
        elif "," in text:
            kws = [k.strip() for k in text.split(",")]
        elif "\n" in text:
            kws = [k.strip() for k in text.split("\n")]
        else:
            kws = [text.strip()]

        keywords.extend([k for k in kws if k and len(k) > 1])

    # METHOD 3: Look for <strong>Keywords:</strong> followed by text
    for strong in soup.find_all("strong"):
        if re.search(r"^keywords?:?$", strong.get_text(), re.I):
            # Get the next text node or paragraph
            parent = strong.parent
            if parent:
                text = parent.get_text()
                text = re.sub(r"^keywords?[\s:;\-–—]*", "", text, flags=re.I)

                if ";" in text:
                    kws = [k.strip() for k in text.split(";")]
                elif "," in text:
                    kws = [k.strip() for k in text.split(",")]
                else:
                    kws = [text.strip()]

                keywords.extend([k for k in kws if k and len(k) > 1])
                break

    # METHOD 4: Look for front-matter abstract/keyword pattern
    front_matter = soup.find("section", class_="front-matter")
    if front_matter:
        kwd_group = front_matter.find(
            ["section", "div"], class_=re.compile(r"kwd", re.I)
        )
        if kwd_group:
            text = kwd_group.get_text()
            text = re.sub(r"^keywords?[\s:;\-–—]*", "", text, flags=re.I)

            if ";" in text or "," in text:
                delimiter = ";" if ";" in text else ","
                kws = [k.strip() for k in text.split(delimiter)]
                keywords.extend([k for k in kws if k and len(k) > 1])

    # Clean up and deduplicate
    keywords = list(set([k for k in keywords if k and len(k) > 1 and len(k) < 100]))

    return keywords


def extract_keywords_from_abstract(
    soup: BeautifulSoup, sections: Dict[str, str]
) -> List[str]:
    """
    Fallback: Extract basic keywords from abstract using simple NLP
    Returns common noun phrases and important terms
    """
    keywords = []

    # Get abstract text
    abstract_text = sections.get("abstract", "")
    if not abstract_text or len(abstract_text) < 50:
        return keywords

    # Convert to lowercase for matching
    text_lower = abstract_text.lower()

    # Common scientific terms that are often keywords
    scientific_terms = [
        "microgravity",
        "spaceflight",
        "stem cells",
        "gene expression",
        "cell culture",
        "tissue engineering",
        "bone loss",
        "muscle atrophy",
        "radiation",
        "oxidative stress",
        "immune system",
        "cardiovascular",
        "cell proliferation",
        "differentiation",
        "apoptosis",
        "bioreactor",
        "scaffold",
        "extracellular matrix",
        "collagen",
        "mechanotransduction",
        "circadian rhythm",
        "metabolism",
        "inflammation",
        "wound healing",
    ]

    for term in scientific_terms:
        if term in text_lower:
            keywords.append(term)

    # Extract capitalized phrases (often important terms)
    capitalized_phrases = re.findall(
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", abstract_text
    )
    keywords.extend(
        [
            p
            for p in capitalized_phrases
            if len(p) > 4 and p not in ["The", "This", "These", "Methods", "Results"]
        ]
    )

    # Remove duplicates and return top 10
    keywords = list(set(keywords))
    return keywords[:10]


def extract_author_affiliations(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract detailed author information with affiliations"""
    authors = []

    # Get author names
    author_metas = soup.find_all("meta", {"name": "citation_author"})

    for author_meta in author_metas:
        author_name = author_meta.get("content", "").strip()

        # Try to find affiliation
        affiliation = None
        affiliation_meta = author_meta.find_next_sibling(
            "meta", {"name": "citation_author_institution"}
        )
        if affiliation_meta:
            affiliation = affiliation_meta.get("content", "").strip()

        # Try to find email
        email = None
        email_meta = author_meta.find_next_sibling(
            "meta", {"name": "citation_author_email"}
        )
        if email_meta:
            email = email_meta.get("content", "").strip()

        authors.append(
            {"name": author_name, "affiliation": affiliation, "email": email}
        )

    # Fallback: simple list if detailed extraction fails
    if not authors:
        author_metas = soup.find_all("meta", {"name": "citation_author"})
        authors = [
            {"name": m.get("content", "").strip(), "affiliation": None, "email": None}
            for m in author_metas
        ]

    return authors


def extract_pmcid_and_pmid(
    soup: BeautifulSoup, filename: str
) -> Dict[str, Optional[str]]:
    """Extract PMCID and PMID"""
    ids = {"pmcid": None, "pmid": None}

    # PMCID from filename
    pmcid_match = re.search(r"PMC\d+", filename, re.I)
    if pmcid_match:
        ids["pmcid"] = pmcid_match.group(0).upper()

    # PMCID from meta
    pmcid_meta = soup.find("meta", {"name": "citation_pmcid"})
    if pmcid_meta:
        ids["pmcid"] = pmcid_meta.get("content", "").strip()

    # PMID from meta
    pmid_meta = soup.find("meta", {"name": "citation_pmid"})
    if pmid_meta:
        ids["pmid"] = pmid_meta.get("content", "").strip()

    return ids


def extract_urls(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract relevant URLs"""
    urls = {"fulltext_html": None, "fulltext_pdf": None, "abstract": None}

    # HTML full text
    html_url = soup.find("meta", {"name": "citation_fulltext_html_url"})
    if html_url:
        urls["fulltext_html"] = html_url.get("content", "").strip()

    # PDF
    pdf_url = soup.find("meta", {"name": "citation_pdf_url"})
    if pdf_url:
        urls["fulltext_pdf"] = pdf_url.get("content", "").strip()

    # Abstract URL
    abstract_url = soup.find("meta", {"name": "citation_abstract_html_url"})
    if abstract_url:
        urls["abstract"] = abstract_url.get("content", "").strip()

    return urls


def extract_figures_and_tables(soup: BeautifulSoup) -> Dict[str, int]:
    """Count figures and tables"""
    counts = {"figure_count": 0, "table_count": 0}

    # Count figures
    figures = soup.find_all(["figure", "div"], class_=re.compile(r"fig", re.I))
    counts["figure_count"] = len(figures)

    # Count tables
    tables = soup.find_all("table")
    counts["table_count"] = len(tables)

    return counts


def extract_references_count(soup: BeautifulSoup) -> int:
    """Count references"""
    # Try to find references section
    ref_section = soup.find(["div", "section"], class_=re.compile(r"ref", re.I))
    if ref_section:
        # Count citation elements
        citations = ref_section.find_all(
            ["li", "div"], class_=re.compile(r"ref|citation", re.I)
        )
        return len(citations)

    # Fallback: count reference meta tags
    ref_metas = soup.find_all("meta", {"name": "citation_reference"})
    return len(ref_metas)


def detect_nasa_mentions(soup: BeautifulSoup) -> Dict[str, any]:
    """Detect NASA-specific content"""
    full_text = soup.get_text().lower()

    nasa_info = {
        "mentions_nasa": "nasa" in full_text,
        "mentions_iss": any(
            term in full_text for term in ["iss", "international space station"]
        ),
        "mentions_microgravity": "microgravity" in full_text
        or "micro-gravity" in full_text,
        "mentions_spaceflight": "spaceflight" in full_text
        or "space flight" in full_text,
        "mentions_radiation": "radiation" in full_text and "space" in full_text,
    }

    # Count NASA mentions
    nasa_info["nasa_mention_count"] = full_text.count("nasa")

    return nasa_info


def extract_funding_info(soup: BeautifulSoup, sections: Dict[str, str]) -> List[str]:
    """Extract funding information"""
    funding_sources = []

    # Check funding section
    if "funding" in sections:
        funding_text = sections["funding"]
        # Look for grant numbers (common patterns)
        grant_numbers = re.findall(r"\b[A-Z]{2,5}[-\s]?\d{4,10}\b", funding_text)
        funding_sources.extend(grant_numbers)

        # Look for agency names
        agencies = ["NASA", "NIH", "NSF", "ESA", "JAXA", "Roscosmos"]
        for agency in agencies:
            if agency.lower() in funding_text.lower():
                funding_sources.append(agency)

    return list(set(funding_sources))


def extract_article_data(file_path: str) -> dict:
    """Enhanced article data extraction"""
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    filename = os.path.basename(file_path)

    # Extract IDs
    ids = extract_pmcid_and_pmid(soup, filename)

    data = {
        "pmcid": ids["pmcid"] or filename.replace(".html", ""),
        "pmid": ids["pmid"],
        "title": None,
        "authors": [],
        "sections": {},
        "metadata": {},
    }

    # --- Title ---
    meta_title = soup.find("meta", {"name": "citation_title"})
    if meta_title:
        data["title"] = meta_title.get("content", "").strip()
    elif soup.title:
        data["title"] = soup.title.get_text(strip=True)

    # --- Authors (enhanced) ---
    data["authors"] = extract_author_affiliations(soup)

    # --- Sections ---
    headers = soup.find_all(["h2", "h3", "h4"])
    for header in headers:
        name = normalize_section_name(header.get_text())
        if not name or name in ["references", "footnotes"]:  # Skip references
            continue

        content_parts = []
        for sib in header.find_next_siblings():
            if sib.name in ["h2", "h3", "h4"]:  # stop at next section
                break
            if sib.name == "p":
                content_parts.append(sib.get_text(" ", strip=True))
            # Also capture content in divs (some articles use div instead of p)
            elif sib.name == "div" and sib.find("p"):
                for p in sib.find_all("p"):
                    content_parts.append(p.get_text(" ", strip=True))

        if content_parts:
            data["sections"][name] = " ".join(content_parts)

    # --- Metadata ---
    data["metadata"]["publication_date"] = extract_publication_date(soup)
    data["metadata"]["doi"] = extract_doi(soup)

    journal_info = extract_journal_info(soup)
    data["metadata"].update(journal_info)

    data["metadata"]["keywords"] = extract_keywords_from_meta(soup)

    # If no keywords found, try extracting from abstract
    if not data["metadata"]["keywords"]:
        data["metadata"]["keywords"] = extract_keywords_from_abstract(
            soup, data["sections"]
        )

    data["metadata"]["urls"] = extract_urls(soup)

    fig_table_counts = extract_figures_and_tables(soup)
    data["metadata"].update(fig_table_counts)

    data["metadata"]["reference_count"] = extract_references_count(soup)

    nasa_info = detect_nasa_mentions(soup)
    data["metadata"]["nasa_info"] = nasa_info

    data["metadata"]["funding_sources"] = extract_funding_info(soup, data["sections"])

    # Calculate word counts for sections
    data["metadata"]["section_word_counts"] = {
        section: len(content.split()) for section, content in data["sections"].items()
    }
    data["metadata"]["total_word_count"] = sum(
        data["metadata"]["section_word_counts"].values()
    )

    # Store original file path
    data["metadata"]["source_file"] = file_path

    return data


def batch_extract():
    """Extract all articles with enhanced metadata"""
    all_data = []
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".html")]
    print(f"Found {len(files)} HTML files to process...")

    stats = {
        "total": len(files),
        "success": 0,
        "errors": 0,
        "with_doi": 0,
        "with_date": 0,
        "with_keywords": 0,
        "nasa_related": 0,
    }

    for i, filename in enumerate(files, 1):
        try:
            article = extract_article_data(os.path.join(INPUT_DIR, filename))
            all_data.append(article)

            # Update stats
            stats["success"] += 1
            if article["metadata"].get("doi"):
                stats["with_doi"] += 1
            if article["metadata"].get("publication_date"):
                stats["with_date"] += 1
            if article["metadata"].get("keywords"):
                stats["with_keywords"] += 1
            if article["metadata"]["nasa_info"]["mentions_nasa"]:
                stats["nasa_related"] += 1

            print(f"[{i}/{len(files)}] ✅ {filename}")

        except Exception as e:
            stats["errors"] += 1
            print(f"[{i}/{len(files)}] ❌ {filename}: {e}")

    # Save JSON (full data)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    # Save CSV (flattened for quick view)
    df = pd.DataFrame(
        [
            {
                "pmcid": a["pmcid"],
                "pmid": a["pmid"],
                "title": a["title"],
                "author_count": len(a["authors"]),
                "first_author": a["authors"][0]["name"] if a["authors"] else None,
                "publication_date": a["metadata"].get("publication_date"),
                "journal": a["metadata"].get("journal"),
                "doi": a["metadata"].get("doi"),
                "abstract": a["sections"].get("abstract", ""),
                "keywords": "; ".join(a["metadata"].get("keywords", [])),
                "section_count": len(a["sections"]),
                "total_words": a["metadata"].get("total_word_count", 0),
                "nasa_related": a["metadata"]["nasa_info"]["mentions_nasa"],
                "mentions_iss": a["metadata"]["nasa_info"]["mentions_iss"],
                "mentions_microgravity": a["metadata"]["nasa_info"][
                    "mentions_microgravity"
                ],
            }
            for a in all_data
        ]
    )
    df.to_csv(OUTPUT_CSV, index=False)

    # Save metadata-only CSV
    metadata_df = pd.DataFrame(
        [
            {
                "pmcid": a["pmcid"],
                "doi": a["metadata"].get("doi"),
                "publication_date": a["metadata"].get("publication_date"),
                "journal": a["metadata"].get("journal"),
                "volume": a["metadata"].get("volume"),
                "issue": a["metadata"].get("issue"),
                "pages": a["metadata"].get("pages"),
                "figure_count": a["metadata"].get("figure_count", 0),
                "table_count": a["metadata"].get("table_count", 0),
                "reference_count": a["metadata"].get("reference_count", 0),
                "keyword_count": len(a["metadata"].get("keywords", [])),
                "funding_sources": "; ".join(a["metadata"].get("funding_sources", [])),
            }
            for a in all_data
        ]
    )
    metadata_df.to_csv(OUTPUT_METADATA_CSV, index=False)

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Total files: {stats['total']}")
    print(f"Successfully processed: {stats['success']}")
    print(f"Errors: {stats['errors']}")
    print(
        f"Articles with DOI: {stats['with_doi']} ({stats['with_doi']/stats['success']*100:.1f}%)"
    )
    print(
        f"Articles with date: {stats['with_date']} ({stats['with_date']/stats['success']*100:.1f}%)"
    )
    print(
        f"Articles with keywords: {stats['with_keywords']} ({stats['with_keywords']/stats['success']*100:.1f}%)"
    )
    print(
        f"NASA-related articles: {stats['nasa_related']} ({stats['nasa_related']/stats['success']*100:.1f}%)"
    )
    print(f"\nFiles saved:")
    print(f"  - {OUTPUT_JSON} (complete data)")
    print(f"  - {OUTPUT_CSV} (main data table)")
    print(f"  - {OUTPUT_METADATA_CSV} (metadata only)")


if __name__ == "__main__":
    batch_extract()
