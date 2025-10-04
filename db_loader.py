"""
NASA Bioscience Publications Data Loader - UPDATED FOR ENHANCED EXTRACTOR
Processes enhanced JSON structure and populates PostgreSQL database
"""

import json
import re
from typing import List, Tuple, Optional
import psycopg2
from psycopg2.extras import execute_batch
import spacy
from collections import Counter
import os
from datetime import datetime
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


INPUT_JSON = "articles_detailed.json"

# Load spaCy model for NLP
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print(
        "Warning: spaCy model not found. Run: python -m spacy download en_core_web_sm"
    )
    nlp = None

# ============================================
# Keyword Extractor
# ============================================


class KeywordExtractor:
    """Extract relevant keywords and entities from scientific text"""

    ORGANISMS = {
        "human",
        "humans",
        "mouse",
        "mice",
        "rat",
        "rats",
        "arabidopsis",
        "c. elegans",
        "drosophila",
        "zebrafish",
        "e. coli",
        "yeast",
        "cell culture",
        "stem cells",
        "osteoblast",
        "fibroblast",
        "mc3t3",
        "macaca",
        "rhesus monkey",
        "nonhuman primate",
        "dog",
        "canine",
        "cat",
        "feline",
        "pig",
        "porcine",
        "rabbit",
        "chicken",
        "avian",
        "bacteria",
        "microbiome",
        "microbes",
        "virus",
        "fungi",
        "plants",
        "seedlings",
        "wheat",
        "rice",
        "corn",
        "soybean",
        "barley",
        "algae",
    }

    EXPERIMENT_TYPES = {
        "microgravity",
        "spaceflight",
        "simulated microgravity",
        "radiation",
        "cosmic radiation",
        "isolation",
        "confinement",
        "hypergravity",
        "parabolic flight",
        "ground control",
        "iss",
        "space shuttle",
        "rotating wall vessel",
        "clinostat",
        "bed rest",
        "hindlimb unloading",
        "head-down tilt",
        "bioreactor",
        "random positioning machine",
        "space analog habitat",
        "antarctic isolation",
        "mars analog",
        "lunar analog",
        "exposure facility",
        "biosatellite",
        "high-altitude balloon",
        "centrifuge experiment",
    }

    BIOLOGICAL_SYSTEMS = {
        "bone",
        "muscle",
        "cardiovascular",
        "immune",
        "nervous system",
        "gene expression",
        "cell proliferation",
        "differentiation",
        "metabolism",
        "circadian rhythm",
        "stress response",
        "mineralization",
        "osteogenesis",
        "cell culture",
        "tissue engineering",
        "hematopoiesis",
        "angiogenesis",
        "neuroplasticity",
        "synaptic function",
        "mitochondrial function",
        "oxidative stress",
        "apoptosis",
        "autophagy",
        "inflammation",
        "cytokine response",
        "endocrine",
        "hormone signaling",
        "microbiome",
        "gut-brain axis",
        "wound healing",
        "regeneration",
        "epigenetics",
        "DNA repair",
        "chromatin remodeling",
        "protein folding",
        "proteostasis",
        "cell adhesion",
        "extracellular matrix",
        "oncogenesis",
        "tumor growth",
        "cancer models",
        "aging",
        "senescence",
        "longevity",
    }

    def __init__(self):
        self.nlp = nlp

    def extract_keywords(
        self, text: str, max_keywords: int = 25
    ) -> List[Tuple[str, str, float]]:
        """Extract keywords with categories and relevance scores"""
        if not text or not self.nlp:
            return []

        text = text[:50000]
        doc = self.nlp(text.lower())
        keywords = []

        # Extract organisms
        for token in doc:
            if token.lemma_ in self.ORGANISMS:
                keywords.append((token.lemma_, "organism", 1.0))

        # Extract experiment types
        for exp_type in self.EXPERIMENT_TYPES:
            if exp_type in text.lower():
                keywords.append((exp_type, "experiment_type", 1.0))

        # Extract biological systems
        for bio_sys in self.BIOLOGICAL_SYSTEMS:
            if bio_sys in text.lower():
                keywords.append((bio_sys, "biological_system", 0.8))

        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "NORP"] and len(ent.text) > 3:
                keywords.append((ent.text, "entity", 0.6))

        # Extract noun phrases
        noun_phrases = [
            chunk.text for chunk in doc.noun_chunks if 1 <= len(chunk.text.split()) <= 3
        ]
        phrase_counts = Counter(noun_phrases)

        for phrase, count in phrase_counts.most_common(15):
            if count > 1 and len(phrase) > 4:
                relevance = min(count / 10.0, 1.0)
                keywords.append((phrase, "topic", relevance))

        # Remove duplicates
        unique_keywords = {}
        for kw, cat, score in keywords:
            if kw not in unique_keywords or unique_keywords[kw][1] < score:
                unique_keywords[kw] = (cat, score)

        result = [(kw, cat, score) for kw, (cat, score) in unique_keywords.items()]
        result.sort(key=lambda x: x[2], reverse=True)

        return result[:max_keywords]


# ============================================
# Database Loader
# ============================================


class DatabaseLoader:
    """Load enhanced article data into PostgreSQL"""

    def __init__(self, db_config: dict):
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()
        self.extractor = KeywordExtractor() if nlp else None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def normalize_date(self, date_str: str):
        if not date_str or date_str.strip() == "":
            return None
        try:
            # Try YYYY-MM-DD first
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
        try:
            # Try YYYY Mon (e.g., 2013 Jan)
            return datetime.strptime(date_str, "%Y %b").date()
        except ValueError:
            pass
        try:
            # Try just YYYY
            return datetime.strptime(date_str, "%Y").date()
        except ValueError:
            return None  # fallback if unrecognized

    def parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse date string to PostgreSQL-compatible format"""
        if not date_str:
            return None
        try:
            # Already in YYYY-MM-DD format
            if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                return date_str
            # Year only
            if re.match(r"^\d{4}$", date_str):
                return f"{date_str}-01-01"
            return date_str
        except:
            return None

    def load_article(self, article_data: dict) -> int:
        """Load article with enhanced metadata"""
        pmcid = article_data["pmcid"]
        pmid = article_data.get("pmid")
        title = article_data.get("title", "Untitled")

        metadata = article_data.get("metadata", {})
        pub_date = self.parse_date(metadata.get("publication_date"))
        pub_date = self.normalize_date(pub_date)

        journal = metadata.get("journal")
        doi = metadata.get("doi")

        self.cursor.execute(
            """
            INSERT INTO articles (pmcid, title, publication_date, journal, doi)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (pmcid) DO UPDATE 
            SET title = EXCLUDED.title,
                publication_date = EXCLUDED.publication_date,
                journal = EXCLUDED.journal,
                doi = EXCLUDED.doi
            RETURNING id
        """,
            (pmcid, title, pub_date, journal, doi),
        )

        article_id = self.cursor.fetchone()[0]
        return article_id

    def load_authors(self, article_id: int, authors_data: List):
        """Load authors with enhanced information (affiliations, emails)"""
        if not authors_data:
            return

        for position, author_info in enumerate(authors_data, 1):
            # Handle both old format (string) and new format (dict)
            if isinstance(author_info, str):
                author_name = author_info
                affiliation = None
                email = None
            else:
                author_name = author_info.get("name", "")
                affiliation = author_info.get("affiliation")
                email = author_info.get("email")

            if not author_name:
                continue

            normalized = self._normalize_author_name(author_name)

            # Insert or get author
            self.cursor.execute(
                """
                INSERT INTO authors (full_name, normalized_name)
                VALUES (%s, %s)
                ON CONFLICT (normalized_name) DO UPDATE 
                SET full_name = EXCLUDED.full_name
                RETURNING id
            """,
                (author_name, normalized),
            )

            author_id = self.cursor.fetchone()[0]

            # Link to article
            self.cursor.execute(
                """
                INSERT INTO article_authors (article_id, author_id, author_position)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """,
                (article_id, author_id, position),
            )

    def load_sections(self, article_id: int, sections: dict):
        """Load article sections with word counts"""
        if not sections:
            return

        section_data = []
        for order, (section_type, content) in enumerate(sections.items(), 1):
            if content and content.strip():
                word_count = len(content.split())
                section_data.append(
                    (article_id, section_type, content, word_count, order)
                )

        if section_data:
            execute_batch(
                self.cursor,
                """
                INSERT INTO article_sections 
                (article_id, section_type, content, word_count, section_order)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """,
                section_data,
            )

    def load_metadata(self, article_id: int, article_data: dict):
        """Store complete article data including enhanced metadata as JSONB"""
        metadata = article_data.get("metadata", {})
        sections = article_data.get("sections", {})

        # Prepare custom fields from metadata
        custom_fields = {
            "volume": metadata.get("volume"),
            "issue": metadata.get("issue"),
            "pages": metadata.get("pages"),
            "issn": metadata.get("issn"),
            "figure_count": metadata.get("figure_count", 0),
            "table_count": metadata.get("table_count", 0),
            "reference_count": metadata.get("reference_count", 0),
            "total_word_count": metadata.get("total_word_count", 0),
            "urls": metadata.get("urls", {}),
            "nasa_info": metadata.get("nasa_info", {}),
            "funding_sources": metadata.get("funding_sources", []),
        }

        sections_json = json.dumps(sections)
        custom_json = json.dumps(custom_fields)
        html_path = metadata.get("source_file")

        self.cursor.execute(
            """
            INSERT INTO article_metadata 
            (article_id, all_sections, raw_html_path, custom_fields)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (article_id) DO UPDATE 
            SET all_sections = EXCLUDED.all_sections,
                custom_fields = EXCLUDED.custom_fields
        """,
            (article_id, sections_json, html_path, custom_json),
        )

    def load_author_keywords(self, article_id: int, keywords: List[str]):
        """Load author-provided keywords from metadata"""
        if not keywords:
            return

        for keyword in keywords:
            if not keyword or len(keyword) < 2:
                continue

            keyword_clean = keyword.strip().lower()

            self.cursor.execute(
                """
                INSERT INTO keywords (keyword, category)
                VALUES (%s, %s)
                ON CONFLICT (keyword) DO UPDATE SET category = EXCLUDED.category
                RETURNING id
            """,
                (keyword_clean, "author_provided"),
            )

            keyword_id = self.cursor.fetchone()[0]

            self.cursor.execute(
                """
                INSERT INTO article_keywords 
                (article_id, keyword_id, relevance_score, extraction_method)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """,
                (article_id, keyword_id, 1.0, "author"),
            )

    def extract_and_load_keywords(self, article_id: int, article_data: dict):
        """Extract keywords using NLP"""
        if not self.extractor:
            return

        sections = article_data.get("sections", {})
        text_for_extraction = ""

        for section in ["abstract", "conclusions", "results"]:
            if section in sections:
                text_for_extraction += " " + sections[section]

        if not text_for_extraction.strip():
            return

        keywords = self.extractor.extract_keywords(text_for_extraction)

        for keyword, category, relevance in keywords:
            self.cursor.execute(
                """
                INSERT INTO keywords (keyword, category)
                VALUES (%s, %s)
                ON CONFLICT (keyword) DO UPDATE SET category = EXCLUDED.category
                RETURNING id
            """,
                (keyword, category),
            )

            keyword_id = self.cursor.fetchone()[0]

            self.cursor.execute(
                """
                INSERT INTO article_keywords 
                (article_id, keyword_id, relevance_score, extraction_method)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """,
                (article_id, keyword_id, relevance, "nlp_auto"),
            )

    def load_organisms_from_keywords(self, article_id: int, article_data: dict):
        """Load organisms from auto-extracted keywords and author keywords"""
        metadata = article_data.get("metadata", {})
        author_keywords = metadata.get("keywords", [])

        # Common organism keywords
        organism_indicators = [
            "mouse",
            "mice",
            "rat",
            "human",
            "cell",
            "arabidopsis",
            "drosophila",
            "zebrafish",
            "c. elegans",
            "e. coli",
            "osteoblast",
            "fibroblast",
            "stem cell",
        ]

        found_organisms = set()

        # Check author keywords
        for kw in author_keywords:
            kw_lower = kw.lower()
            for org in organism_indicators:
                if org in kw_lower:
                    found_organisms.add(org)

        # Check abstract and methods
        sections = article_data.get("sections", {})
        search_text = ""
        for section in ["abstract", "materials_and_methods"]:
            if section in sections:
                search_text += " " + sections[section].lower()

        for org in organism_indicators:
            if org in search_text:
                found_organisms.add(org)

        # Store organisms
        for organism in found_organisms:
            self.cursor.execute(
                """
                INSERT INTO organisms (scientific_name, common_name, organism_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (scientific_name) DO NOTHING
                RETURNING id
            """,
                (organism, organism, "detected"),
            )

            result = self.cursor.fetchone()
            if result:
                organism_id = result[0]
                self.cursor.execute(
                    """
                    INSERT INTO article_organisms (article_id, organism_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """,
                    (article_id, organism_id),
                )

    def load_nasa_experiments(self, article_id: int, article_data: dict):
        """Detect and load NASA experiment information"""
        metadata = article_data.get("metadata", {})
        nasa_info = metadata.get("nasa_info", {})

        # Create experiment entries based on detected NASA content
        if nasa_info.get("mentions_iss"):
            self._link_to_experiment(
                article_id, "ISS Experiments", "ISS", "microgravity"
            )

        if nasa_info.get("mentions_microgravity"):
            self._link_to_experiment(
                article_id, "Microgravity Research", "Various", "microgravity"
            )

        if nasa_info.get("mentions_spaceflight"):
            self._link_to_experiment(
                article_id, "Spaceflight Studies", "Various", "spaceflight"
            )

    def _link_to_experiment(
        self, article_id: int, exp_name: str, mission: str, exp_type: str
    ):
        """Helper to link article to experiment"""
        self.cursor.execute(
            """
            INSERT INTO nasa_experiments (experiment_name, mission, experiment_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (experiment_name) DO NOTHING
            RETURNING id
        """,
            (exp_name, mission, exp_type),
        )

        result = self.cursor.fetchone()
        if result:
            exp_id = result[0]
            self.cursor.execute(
                """
                INSERT INTO article_experiments (article_id, experiment_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """,
                (article_id, exp_id),
            )

    def _normalize_author_name(self, name: str) -> str:
        """Normalize author names for deduplication"""
        name = re.sub(r"\s+", " ", name.strip())
        return name.title()

    def process_article(self, article_data: dict):
        """Process a complete article with enhanced metadata"""
        try:
            # 1. Load article with metadata
            article_id = self.load_article(article_data)

            # 2. Load authors (handles both old and new format)
            authors = article_data.get("authors", [])
            if authors:
                self.load_authors(article_id, authors)

            # 3. Load sections
            sections = article_data.get("sections", {})
            if sections:
                self.load_sections(article_id, sections)

            # 4. Store complete metadata as JSONB
            self.load_metadata(article_id, article_data)

            # 5. Load author-provided keywords
            metadata = article_data.get("metadata", {})
            author_keywords = metadata.get("keywords", [])
            if author_keywords:
                self.load_author_keywords(article_id, author_keywords)

            # 6. Auto-extract keywords using NLP
            if self.extractor:
                self.extract_and_load_keywords(article_id, article_data)

            # 7. Load organisms
            self.load_organisms_from_keywords(article_id, article_data)

            # 8. Link to NASA experiments
            self.load_nasa_experiments(article_id, article_data)

            self.conn.commit()
            return article_id

        except Exception as e:
            self.conn.rollback()
            raise Exception(
                f"Error processing {article_data.get('pmcid', 'unknown')}: {str(e)}"
            )


# ============================================
# Main Processing
# ============================================


def load_all_articles(json_file: str, db_config: dict, batch_size: int = 50):
    """Load all articles from enhanced JSON"""

    print("Loading articles from JSON...")
    with open(json_file, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Found {len(articles)} articles to process\n")

    processed = 0
    errors = []

    with DatabaseLoader(db_config) as loader:
        for i, article in enumerate(articles, 1):
            try:
                article_id = loader.process_article(article)
                processed += 1

                if i % batch_size == 0:
                    print(f"✓ Processed {i}/{len(articles)} articles...")

            except Exception as e:
                pmcid = article.get("pmcid", "unknown")
                errors.append((pmcid, str(e)))
                print(f"✗ {pmcid}: {e}")

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Successfully processed: {processed}/{len(articles)}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nFailed articles (first 10):")
        for pmcid, error in errors[:10]:
            print(f"  - {pmcid}: {error}")

    return processed, errors


def print_database_stats(db_config: dict):
    """Print comprehensive database statistics"""
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)

    # Articles with metadata
    cursor.execute(
        """
        SELECT 
            COUNT(*) as total,
            COUNT(doi) as with_doi,
            COUNT(publication_date) as with_date,
            COUNT(journal) as with_journal
        FROM articles
    """
    )
    total, doi, date, journal = cursor.fetchone()
    print(f"\nArticles: {total}")
    print(f"  With DOI: {doi} ({doi/total*100:.1f}%)")
    print(f"  With date: {date} ({date/total*100:.1f}%)")
    print(f"  With journal: {journal} ({journal/total*100:.1f}%)")

    # Authors
    cursor.execute("SELECT COUNT(*) FROM authors")
    print(f"\nUnique authors: {cursor.fetchone()[0]}")

    # Sections
    cursor.execute(
        """
        SELECT section_type, COUNT(*) 
        FROM article_sections 
        GROUP BY section_type 
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """
    )
    print("\nTop sections:")
    for section, count in cursor.fetchall():
        print(f"  {section}: {count}")

    # Keywords
    cursor.execute(
        """
        SELECT category, COUNT(*) 
        FROM keywords 
        GROUP BY category 
        ORDER BY COUNT(*) DESC
    """
    )
    print("\nKeywords by category:")
    for category, count in cursor.fetchall():
        print(f"  {category}: {count}")

    # Top keywords
    cursor.execute(
        """
        SELECT k.keyword, k.category, COUNT(ak.article_id) as cnt
        FROM keywords k
        JOIN article_keywords ak ON k.id = ak.keyword_id
        GROUP BY k.keyword, k.category
        ORDER BY cnt DESC
        LIMIT 15
    """
    )
    print("\nTop 15 keywords:")
    for keyword, cat, count in cursor.fetchall():
        print(f"  {keyword} ({cat}): {count} articles")

    # NASA-related stats
    cursor.execute(
        """
        SELECT COUNT(*) 
        FROM article_metadata
        WHERE custom_fields->'nasa_info'->>'mentions_nasa' = 'true'
    """
    )
    nasa_count = cursor.fetchone()[0]
    print(f"\nNASA-related articles: {nasa_count} ({nasa_count/total*100:.1f}%)")

    # Organisms
    cursor.execute("SELECT COUNT(*) FROM organisms")
    print(f"\nDetected organisms: {cursor.fetchone()[0]}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    print("NASA Bioscience Data Loader - Enhanced Version")
    print("=" * 60)

    # Process articles
    processed, errors = load_all_articles(INPUT_JSON, DB_CONFIG)

    # Show statistics
    if processed > 0:
        print_database_stats(DB_CONFIG)

    print("\n✓ Complete!")
    print("\nNext steps:")
    print("1. Review statistics above")
    print("2. Test queries on the data")
    print("3. Build dashboard queries")
    print("4. Consider semantic search setup (pgvector)")
