"""
Enhanced NASA Bioscience Article Extractor with Citation Counts
Extracts comprehensive metadata from PMC HTML files including citation counts
"""

import re
from bs4 import BeautifulSoup
import os, json, pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
import requests
import time
import csv
import spacy
from collections import Counter

# Corrected spaCy loading
try:
    nlp = spacy.load("en_core_web_sm")
    # Increase the max_length to handle longer abstracts (e.g., 2 million characters)
    nlp.max_length = 2000000
except OSError:
    print("spaCy model 'en_core_web_sm' not found. Please run:")
    print("python -m spacy download en_core_web_sm")
    nlp = None


INPUT_DIR = "scraped_html_files"
OUTPUT_JSON = "articles_detailed.json"
OUTPUT_CSV = "articles_detailed.csv"
OUTPUT_METADATA_CSV = "articles_metadata.csv"
CITATION_CACHE_FILE = "citation_cache.json"

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


class CitationCounter:
    """Handles PubMed citation counting with caching"""

    def __init__(
        self,
        email: str = "smithsaruni16@@gmail.com",
        api_key: str = None,
        cache_file: str = CITATION_CACHE_FILE,
    ):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        self.cache_file = cache_file
        self.citation_cache = self._load_cache()

    def _load_cache(self) -> Dict[str, int]:
        """Load citation cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_cache(self):
        """Save citation cache to file"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.citation_cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save citation cache: {e}")

    def get_citation_count(self, pmid: str) -> int:
        """
        Get citation count for a PMID with caching
        """
        # Check cache first
        if pmid in self.citation_cache:
            return self.citation_cache[pmid]

        try:
            citation_count = self._scrape_citation_count(pmid)
            self.citation_cache[pmid] = citation_count
            self._save_cache()
            return citation_count
        except Exception as e:
            print(f"Error getting citation count for PMID {pmid}: {e}")
            return 0

    def _scrape_citation_count(self, pmid: str) -> int:
        """
        Scrape citation count from PubMed page
        """
        try:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Method 1: Look for citation count in meta tags or specific elements
            citation_meta = soup.find("meta", {"name": "citation_publication_date"})

            # Method 2: Look for "Cited by" text in various elements
            patterns = [
                r"cited by[^\d]*(\d+)",
                r"citations[^\d]*(\d+)",
                r"cited[^\d]*(\d+)",
                r"(\d+)\s*citations?",
            ]

            text_content = soup.get_text().lower()

            for pattern in patterns:
                matches = re.findall(pattern, text_content)
                if matches:
                    return int(matches[0])

            # Method 3: Look for specific CSS classes or IDs that might contain citation count
            citation_elements = soup.find_all(
                ["a", "span", "div"], class_=re.compile(r"citation|cited", re.I)
            )
            for element in citation_elements:
                text = element.get_text()
                numbers = re.findall(r"\d+", text)
                if numbers and any(
                    word in text.lower() for word in ["cited", "citation"]
                ):
                    return int(numbers[0])

            return 0

        except Exception as e:
            print(f"Error scraping citations for PMID {pmid}: {e}")
            return 0

    def batch_get_citations(
        self, pmids: List[str], delay: float = 0.5
    ) -> Dict[str, int]:
        """
        Get citation counts for multiple PMIDs with rate limiting
        """
        results = {}
        total = len(pmids)

        for i, pmid in enumerate(pmids, 1):
            if not pmid:
                continue

            print(f"  Getting citations [{i}/{total}]: PMID {pmid}")
            results[pmid] = self.get_citation_count(pmid)

            # Rate limiting to be respectful to PubMed servers
            time.sleep(delay)

        return results

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the citation cache"""
        total = len(self.citation_cache)
        non_zero = len([c for c in self.citation_cache.values() if c > 0])
        zero = total - non_zero
        return {
            "total_cached": total,
            "non_zero_citations": non_zero,
            "zero_citations": zero,
        }


# Initialize citation counter (you can customize email and API key)
citation_counter = CitationCounter(
    email="research@example.com",  # Replace with your email
    api_key=None,  # Optional: add your NCBI API key for higher rate limits
)


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


def extract_keywords_from_meta(soup: BeautifulSoup) -> List[str]:
    """Extract author-provided keywords from meta tags"""
    keywords = []

    # Try various meta tag formats
    keyword_meta = soup.find_all("meta", {"name": "citation_keywords"})
    for meta in keyword_meta:
        kw = meta.get("content", "").strip()
        if kw:
            # Some articles separate keywords with semicolons or commas
            if ";" in kw:
                keywords.extend([k.strip() for k in kw.split(";")])
            elif "," in kw:
                keywords.extend([k.strip() for k in kw.split(",")])
            else:
                keywords.append(kw)

    # Also check for keyword sections in the body
    keyword_sections = soup.find_all(["div", "p"], class_=re.compile(r"keyword", re.I))
    for section in keyword_sections:
        text = section.get_text()
        # Remove "Keywords:" prefix
        text = re.sub(r"^keywords?\s*:?\s*", "", text, flags=re.I)
        kws = [k.strip() for k in re.split(r"[;,]", text) if k.strip()]
        keywords.extend(kws)

    return list(set([k for k in keywords if k and len(k) > 1]))


def extract_keywords_with_spacy(
    sections: Dict[str, str], max_keywords: int = 15
) -> List[str]:
    """
    Extracts keywords from abstract using spaCy's NLP capabilities.
    DIAGNOSTIC VERSION - prints debug info at each step
    """
    if not nlp:
        print("  [KEYWORD DEBUG] spaCy model not loaded")
        return []

    abstract_text = sections.get("abstract", "")

    print(f"\n  [KEYWORD DEBUG] Abstract length: {len(abstract_text)} chars")

    if not abstract_text or len(abstract_text) < 50:
        print(f"  [KEYWORD DEBUG] Abstract too short or missing")
        return []

    # --- Process with spaCy ---
    try:
        print(f"  [KEYWORD DEBUG] Processing with spaCy...")
        doc = nlp(abstract_text)
        print(f"  [KEYWORD DEBUG] Successfully processed. Token count: {len(doc)}")
    except Exception as e:
        print(f"  [KEYWORD DEBUG] spaCy failed: {e}")
        return []

    keywords = []

    # 1. Extract noun chunks
    print(f"  [KEYWORD DEBUG] Extracting noun chunks...")
    chunk_count = 0
    chunk_kept = 0
    for chunk in doc.noun_chunks:
        chunk_count += 1
        clean_chunk = chunk.text.lower().strip()

        # Debug first 5 chunks
        if chunk_count <= 5:
            print(
                f"    Chunk {chunk_count}: '{clean_chunk}' | len={len(clean_chunk)} | root_is_stop={chunk.root.is_stop}"
            )

        if len(clean_chunk) > 4 and chunk.root.is_stop is False:
            keywords.append(clean_chunk)
            chunk_kept += 1

    print(f"  [KEYWORD DEBUG] Found {chunk_count} noun chunks, kept {chunk_kept}")

    # 2. Extract important individual nouns
    print(f"  [KEYWORD DEBUG] Extracting individual nouns...")
    noun_count = 0
    noun_kept = 0
    for token in doc:
        if (
            not token.is_stop
            and not token.is_punct
            and token.pos_ == "NOUN"
            and len(token.text) > 4
        ):
            noun_count += 1
            keywords.append(token.lemma_.lower())
            noun_kept += 1

            # Debug first 5 nouns
            if noun_kept <= 5:
                print(
                    f"    Noun {noun_kept}: '{token.text}' -> lemma: '{token.lemma_.lower()}'"
                )

    print(f"  [KEYWORD DEBUG] Found {noun_count} nouns, kept {noun_kept}")

    # 3. Count frequencies and return the most common keywords
    if not keywords:
        print(f"  [KEYWORD DEBUG] No keywords found after extraction")
        return []

    keyword_counts = Counter(keywords)
    print(f"  [KEYWORD DEBUG] Unique keywords: {len(keyword_counts)}")
    print(f"  [KEYWORD DEBUG] Top 5 by frequency: {keyword_counts.most_common(5)}")

    final_keywords = [kw for kw, count in keyword_counts.most_common(max_keywords)]
    print(f"  [KEYWORD DEBUG] Returning {len(final_keywords)} keywords")

    return final_keywords


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
    """Enhanced article data extraction with citation counts"""
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

    # If no author-provided keywords found, use the new spaCy extractor
    if not data["metadata"]["keywords"]:
        # Call the new, smarter function
        data["metadata"]["keywords"] = extract_keywords_with_spacy(data["sections"])
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

    # --- CITATION COUNT ---
    if data["pmid"]:
        data["metadata"]["citation_count"] = citation_counter.get_citation_count(
            data["pmid"]
        )
    else:
        data["metadata"]["citation_count"] = 0

    # Store original file path
    data["metadata"]["source_file"] = file_path

    return data


def batch_extract():
    """Extract all articles with enhanced metadata and citation counts"""
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
        "with_pmid": 0,
        "with_citations": 0,
    }

    # First pass: extract all data
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
            if article.get("pmid"):
                stats["with_pmid"] += 1
            if article["metadata"].get("citation_count", 0) > 0:
                stats["with_citations"] += 1

            print(
                f"[{i}/{len(files)}] ✅ {filename} - Citations: {article['metadata'].get('citation_count', 0)}"
            )

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
                "citation_count": a["metadata"].get("citation_count", 0),
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
                "pmid": a["pmid"],
                "citation_count": a["metadata"].get("citation_count", 0),
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

    # Print citation cache statistics
    cache_stats = citation_counter.get_cache_stats()

    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Total files: {stats['total']}")
    print(f"Successfully processed: {stats['success']}")
    print(f"Errors: {stats['errors']}")
    print(
        f"Articles with PMID: {stats['with_pmid']} ({stats['with_pmid']/stats['success']*100:.1f}%)"
    )
    print(
        f"Articles with citations data: {stats['with_citations']} ({stats['with_citations']/stats['success']*100:.1f}%)"
    )
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

    # Citation statistics
    citation_counts = [
        a["metadata"].get("citation_count", 0) for a in all_data if a.get("pmid")
    ]
    if citation_counts:
        avg_citations = sum(citation_counts) / len(citation_counts)
        max_citations = max(citation_counts)
        print(f"\nCitation Statistics:")
        print(f"  Average citations: {avg_citations:.1f}")
        print(f"  Maximum citations: {max_citations}")
        print(f"  Total citations: {sum(citation_counts)}")

    print(f"\nCitation Cache:")
    print(f"  Cached entries: {cache_stats['total_cached']}")
    print(f"  Non-zero citations: {cache_stats['non_zero_citations']}")

    print(f"\nFiles saved:")
    print(f"  - {OUTPUT_JSON} (complete data)")
    print(f"  - {OUTPUT_CSV} (main data table)")
    print(f"  - {OUTPUT_METADATA_CSV} (metadata only)")
    print(f"  - {CITATION_CACHE_FILE} (citation cache)")

    # Show top cited papers
    cited_papers = sorted(
        [a for a in all_data if a["metadata"].get("citation_count", 0) > 0],
        key=lambda x: x["metadata"].get("citation_count", 0),
        reverse=True,
    )[:10]

    if cited_papers:
        print(f"\nTop 10 Most Cited Papers:")
        for i, paper in enumerate(cited_papers, 1):
            print(
                f"  {i:2d}. {paper['title'][:80]}... - {paper['metadata'].get('citation_count', 0)} citations"
            )


if __name__ == "__main__":
    batch_extract()
