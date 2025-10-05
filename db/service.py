"""
Complete NASA Bioscience Service Layer
Includes AI insights generation and knowledge graph services
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, text, and_, or_, desc, case
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from contextlib import contextmanager
from collections import defaultdict, Counter
import uuid
import math

from .models import (
    Base,
    Articles,
    Authors,
    ArticleAuthors,
    ArticleSections,
    Keywords,
    ArticleKeywords,
    Organisms,
    NasaExperiments,
    ArticleExperiments,
    ArticleMetadata,
    Users,
    Messages,
    ArticleRelationships,
    Topics,
    ArticleTopics,
    FundingSources,
    ArticleFunding,
)

# Database configuration
DATABASE_URL = "postgresql://neondb_owner:npg_UKaI83EmFtMs@ep-still-bonus-ado41f7e.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Create engine and session factory
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# User & Chat Management Service
# ============================================


class UserService:
    """Manages user accounts and chat history"""

    @staticmethod
    def get_or_create_user(email: str) -> uuid.UUID:
        """Get existing user or create new one"""
        with get_db() as db:
            user = db.query(Users).filter(Users.email == email).first()
            if not user:
                user = Users(email=email)
                db.add(user)
                db.commit()
                db.refresh(user)
            return user.id

    @staticmethod
    def save_message(user_id: uuid.UUID, direction: str, content: str) -> uuid.UUID:
        """Save a chat message (inbound or outbound)"""
        with get_db() as db:
            message = Messages(
                user_id=user_id, direction=direction, text_content=content
            )
            db.add(message)
            db.commit()
            return message.id

    @staticmethod
    def get_chat_history(user_id: uuid.UUID, limit: int = 50) -> List[Dict]:
        """Retrieve recent chat history for a user"""
        with get_db() as db:
            messages = (
                db.query(Messages)
                .filter(Messages.user_id == user_id)
                .order_by(Messages.created_at.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": str(msg.id),
                    "direction": msg.direction,
                    "content": msg.text_content,
                    "timestamp": msg.created_at.isoformat(),
                }
                for msg in reversed(messages)
            ]


# ============================================
# Article Search Service
# ============================================


class ArticleSearchService:
    """Advanced article search with full-text and semantic capabilities"""

    @staticmethod
    def full_text_search(
        query: str, section_types: Optional[List[str]] = None, limit: int = 20
    ) -> List[Dict]:
        """
        Perform full-text search using PostgreSQL tsvector
        Bypasses SQLAlchemy to use native FTS
        Now includes all keywords associated with each article
        """
        with get_db() as db:
            sql = text(
                """
                WITH ranked_articles AS (
                    SELECT DISTINCT ON (a.id)
                        a.id,
                        a.pmcid,
                        a.title,
                        a.publication_date,
                        a.journal,
                        a.doi,
                        s.section_type,
                        ts_rank(s.content_search, plainto_tsquery('english', :query)) as rank,
                        ts_headline('english', 
                            LEFT(s.content, 500), 
                            plainto_tsquery('english', :query),
                            'MaxWords=50, MinWords=25'
                        ) as snippet
                    FROM articles a
                    JOIN article_sections s ON a.id = s.article_id
                    WHERE s.content_search @@ plainto_tsquery('english', :query)
                        AND (:section_filter IS NULL OR s.section_type = ANY(:section_filter))
                    ORDER BY a.id, rank DESC
                    LIMIT :limit
                )
                SELECT 
                    ra.*,
                    COALESCE(
                        ARRAY_AGG(k.keyword ORDER BY k.keyword) FILTER (WHERE k.keyword IS NOT NULL),
                        ARRAY[]::VARCHAR[]
                    ) as keywords
                FROM ranked_articles ra
                LEFT JOIN article_keywords ak ON ra.id = ak.article_id
                LEFT JOIN keywords k ON ak.keyword_id = k.id
                GROUP BY ra.id, ra.pmcid, ra.title, ra.publication_date, 
                         ra.journal, ra.doi, ra.section_type, ra.rank, ra.snippet
                ORDER BY ra.rank DESC
            """
            )

            results = db.execute(
                sql, {"query": query, "section_filter": section_types, "limit": limit}
            ).fetchall()

            return [
                {
                    "article_id": r.id,
                    "pmcid": r.pmcid,
                    "title": r.title,
                    "publication_date": (
                        r.publication_date.isoformat() if r.publication_date else None
                    ),
                    "journal": r.journal,
                    "doi": r.doi,
                    "section": r.section_type,
                    "relevance_score": float(r.rank),
                    "snippet": r.snippet,
                    "keywords": list(r.keywords) if r.keywords else [],
                }
                for r in results
            ]

    @staticmethod
    def search_by_keywords(
        keywords: List[str], min_relevance: float = 0.5, limit: int = 20
    ) -> List[Dict]:
        """Search articles by keywords"""
        with get_db() as db:
            query = (
                db.query(
                    Articles,
                    func.array_agg(Keywords.keyword).label("matched_keywords"),
                    func.avg(ArticleKeywords.relevance_score).label("avg_relevance"),
                )
                .join(ArticleKeywords)
                .join(Keywords)
                .filter(
                    Keywords.keyword.in_([kw.lower() for kw in keywords]),
                    ArticleKeywords.relevance_score >= min_relevance,
                )
                .group_by(Articles.id)
                .order_by(desc("avg_relevance"))
                .limit(limit)
            )

            results = query.all()

            return [
                {
                    "article_id": article.id,
                    "pmcid": article.pmcid,
                    "title": article.title,
                    "publication_date": (
                        article.publication_date.isoformat()
                        if article.publication_date
                        else None
                    ),
                    "matched_keywords": matched_kw,
                    "relevance_score": float(avg_rel),
                }
                for article, matched_kw, avg_rel in results
            ]

    @staticmethod
    def filter_articles(
        nasa_related: Optional[bool] = None,
        organisms: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        has_doi: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """Filter articles by various criteria with pagination"""
        with get_db() as db:
            query = db.query(Articles).join(ArticleMetadata)

            # NASA filter using JSONB query
            if nasa_related is not None:
                if nasa_related:
                    query = query.filter(
                        ArticleMetadata.custom_fields["nasa_info"][
                            "mentions_nasa"
                        ].astext.cast(bool)
                        == True
                    )

            # Date filters
            if date_from:
                query = query.filter(Articles.publication_date >= date_from)
            if date_to:
                query = query.filter(Articles.publication_date <= date_to)

            # DOI filter
            if has_doi is not None:
                if has_doi:
                    query = query.filter(Articles.doi.isnot(None))
                else:
                    query = query.filter(Articles.doi.is_(None))

            # Organism filter
            if organisms:
                query = query.join(Articles.organism).filter(
                    Organisms.scientific_name.in_(organisms)
                )

            # Get total count before pagination
            total = query.count()

            # Apply pagination
            results = query.limit(limit).offset(offset).all()

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "articles": [
                    {
                        "article_id": a.id,
                        "pmcid": a.pmcid,
                        "title": a.title,
                        "publication_date": (
                            a.publication_date.isoformat()
                            if a.publication_date
                            else None
                        ),
                        "journal": a.journal,
                        "doi": a.doi,
                    }
                    for a in results
                ],
            }


# ============================================
# Article Details Service
# ============================================


class ArticleDetailService:
    """Retrieve detailed article information"""

    @staticmethod
    def get_article_full(article_id: int) -> Optional[Dict]:
        """Get complete article with all related data"""
        with get_db() as db:
            article = db.query(Articles).filter(Articles.id == article_id).first()
            if not article:
                return None

            # Get authors
            authors = (
                db.query(Authors, ArticleAuthors.author_position)
                .join(ArticleAuthors)
                .filter(ArticleAuthors.article_id == article_id)
                .order_by(ArticleAuthors.author_position)
                .all()
            )

            # Get sections
            sections = (
                db.query(ArticleSections)
                .filter(ArticleSections.article_id == article_id)
                .order_by(ArticleSections.section_order)
                .all()
            )

            # Get keywords
            keywords = (
                db.query(Keywords, ArticleKeywords.relevance_score)
                .join(ArticleKeywords)
                .filter(ArticleKeywords.article_id == article_id)
                .order_by(ArticleKeywords.relevance_score.desc())
                .all()
            )

            # Get metadata
            metadata = (
                db.query(ArticleMetadata)
                .filter(ArticleMetadata.article_id == article_id)
                .first()
            )

            # Get organisms
            organisms = (
                db.query(Organisms)
                .join(Articles.organism)
                .filter(Articles.id == article_id)
                .all()
            )

            return {
                "id": article.id,
                "pmcid": article.pmcid,
                "title": article.title,
                "publication_date": (
                    article.publication_date.isoformat()
                    if article.publication_date
                    else None
                ),
                "journal": article.journal,
                "doi": article.doi,
                "authors": [
                    {"name": author.full_name, "position": position}
                    for author, position in authors
                ],
                "sections": [
                    {
                        "type": s.section_type,
                        "content": s.content,
                        "word_count": s.word_count,
                    }
                    for s in sections
                ],
                "keywords": [
                    {
                        "keyword": kw.keyword,
                        "category": kw.category,
                        "relevance": float(score),
                    }
                    for kw, score in keywords
                ],
                "organisms": [
                    {"scientific_name": o.scientific_name, "common_name": o.common_name}
                    for o in organisms
                ],
                "metadata": metadata.custom_fields if metadata else {},
            }

    @staticmethod
    def get_related_articles(article_id: int, limit: int = 10) -> List[Dict]:
        """Find related articles based on shared keywords"""
        with get_db() as db:
            sql = text(
                """
                WITH article_keywords AS (
                    SELECT keyword_id
                    FROM article_keywords
                    WHERE article_id = :article_id
                )
                SELECT 
                    a.id,
                    a.pmcid,
                    a.title,
                    a.publication_date,
                    COUNT(DISTINCT ak.keyword_id) as shared_keywords,
                    AVG(ak.relevance_score) as avg_relevance
                FROM articles a
                JOIN article_keywords ak ON a.id = ak.article_id
                WHERE ak.keyword_id IN (SELECT keyword_id FROM article_keywords)
                    AND a.id != :article_id
                GROUP BY a.id, a.pmcid, a.title, a.publication_date
                ORDER BY shared_keywords DESC, avg_relevance DESC
                LIMIT :limit
            """
            )

            results = db.execute(
                sql, {"article_id": article_id, "limit": limit}
            ).fetchall()

            return [
                {
                    "article_id": r.id,
                    "pmcid": r.pmcid,
                    "title": r.title,
                    "publication_date": (
                        r.publication_date.isoformat() if r.publication_date else None
                    ),
                    "shared_keywords": r.shared_keywords,
                    "similarity_score": float(r.avg_relevance),
                }
                for r in results
            ]


# ============================================
# Dashboard Analytics Service
# ============================================


class DashboardService:
    """Provide analytics and metrics for dashboard"""

    @staticmethod
    def get_overview_metrics() -> Dict:
        """Get high-level metrics for dashboard"""
        with get_db() as db:
            total_articles = db.query(func.count(Articles.id)).scalar()

            articles_with_doi = (
                db.query(func.count(Articles.id))
                .filter(Articles.doi.isnot(None))
                .scalar()
            )

            total_authors = db.query(func.count(Authors.id)).scalar()
            total_keywords = db.query(func.count(Keywords.id)).scalar()

            # NASA-related articles count
            nasa_count = db.execute(
                text(
                    """
                SELECT COUNT(*)
                FROM article_metadata
                WHERE custom_fields->'nasa_info'->>'mentions_nasa' = 'true'
            """
                )
            ).scalar()

            # Recent publications (last 2 years)
            two_years_ago = datetime.now() - timedelta(days=730)
            recent_count = (
                db.query(func.count(Articles.id))
                .filter(Articles.publication_date >= two_years_ago)
                .scalar()
            )

            years_of_publication = len(DashboardService.get_publication_timeline())

            return {
                "total_publications": total_articles,
                "publications_with_doi": articles_with_doi,
                "doi_coverage_percent": (
                    round((articles_with_doi / total_articles * 100), 1)
                    if total_articles > 0
                    else 0
                ),
                "total_authors": total_authors,
                "total_keywords": total_keywords,
                "nasa_related_count": nasa_count,
                "nasa_related_percent": (
                    round((nasa_count / total_articles * 100), 1)
                    if total_articles > 0
                    else 0
                ),
                "recent_publications": recent_count,
                "years_of_publication": years_of_publication,
            }

    @staticmethod
    def get_research_areas(limit: int = 10) -> List[Dict]:
        """Auto-discover top research areas by publication count"""
        with get_db() as db:
            results = (
                db.query(
                    Keywords.keyword,
                    Keywords.category,
                    func.count(ArticleKeywords.article_id).label("article_count"),
                )
                .join(ArticleKeywords, Keywords.id == ArticleKeywords.keyword_id)
                .group_by(Keywords.keyword, Keywords.category)
                .order_by(desc("article_count"))
                .limit(limit)
                .all()
            )

            return [
                {
                    "name": r.keyword,
                    "count": r.article_count,
                    "category": r.category or "unknown",
                }
                for r in results
            ]

    @staticmethod
    def get_publication_timeline() -> List[Dict]:
        """Get publications by year"""
        with get_db() as db:
            results = db.execute(
                text(
                    """
                SELECT 
                    EXTRACT(YEAR FROM publication_date) as year,
                    COUNT(*) as count
                FROM articles
                WHERE publication_date IS NOT NULL
                GROUP BY year
                ORDER BY year
            """
                )
            ).fetchall()

            return [
                {"year": int(r.year) if r.year else None, "count": r.count}
                for r in results
            ]

    @staticmethod
    def get_top_authors(limit: int = 20) -> List[Dict]:
        """Get most prolific authors"""
        with get_db() as db:
            results = (
                db.query(
                    Authors.full_name,
                    func.count(ArticleAuthors.article_id).label("article_count"),
                )
                .join(ArticleAuthors)
                .group_by(Authors.id, Authors.full_name)
                .order_by(desc("article_count"))
                .limit(limit)
                .all()
            )

            return [
                {"author": r.full_name, "publication_count": r.article_count}
                for r in results
            ]

    @staticmethod
    def get_keyword_distribution() -> Dict[str, int]:
        """Get keyword counts by category"""
        with get_db() as db:
            results = (
                db.query(Keywords.category, func.count(Keywords.id).label("count"))
                .group_by(Keywords.category)
                .all()
            )

            return {r.category or "uncategorized": r.count for r in results}

    @staticmethod
    def get_organisms_studied(limit: int = 15) -> List[Dict]:
        """Get most studied organisms"""
        with get_db() as db:
            sql = text(
                """
                SELECT 
                    o.scientific_name,
                    o.common_name,
                    COUNT(ao.article_id) as article_count
                FROM organisms o
                JOIN article_organisms ao ON o.id = ao.organism_id
                GROUP BY o.id, o.scientific_name, o.common_name
                ORDER BY article_count DESC
                LIMIT :limit
            """
            )

            results = db.execute(sql, {"limit": limit}).fetchall()

            return [
                {
                    "organism": r.scientific_name,
                    "common_name": r.common_name,
                    "study_count": r.article_count,
                }
                for r in results
            ]

    @staticmethod
    def get_knowledge_gaps() -> List[Dict]:
        """Identify understudied areas (low publication count)"""
        with get_db() as db:
            results = (
                db.query(
                    Keywords.keyword,
                    Keywords.category,
                    func.count(ArticleKeywords.article_id).label("article_count"),
                )
                .join(ArticleKeywords)
                .filter(Keywords.category.in_(["biological_system", "experiment_type"]))
                .group_by(Keywords.keyword, Keywords.category)
                .having(func.count(ArticleKeywords.article_id) < 10)
                .order_by("article_count")
                .limit(15)
                .all()
            )

            # Calculate progress percentage (inverse of gap severity)
            max_expected = 50  # Expected publication count for well-studied area

            return [
                {
                    "area": r.keyword,
                    "category": r.category,
                    "publication_count": r.article_count,
                    "severity": (
                        "Critical"
                        if r.article_count < 3
                        else "High" if r.article_count < 6 else "Medium"
                    ),
                    "progress": min(int((r.article_count / max_expected) * 100), 100),
                }
                for r in results
            ]

    @staticmethod
    def get_analytics_breakdown() -> Dict:
        """Get complete analytics data for charts"""
        with get_db() as db:
            # Publication trends over time
            timeline = DashboardService.get_publication_timeline()

            # Impact distribution (using NASA relevance as proxy)
            impact_sql = text(
                """
                SELECT 
                    CASE 
                        WHEN custom_fields->'nasa_info'->>'mentions_nasa' = 'true' 
                             AND custom_fields->'nasa_info'->>'mentions_iss' = 'true' 
                        THEN 'Critical'
                        WHEN custom_fields->'nasa_info'->>'mentions_nasa' = 'true' 
                        THEN 'High'
                        WHEN custom_fields->>'figure_count' IS NOT NULL 
                             AND (custom_fields->>'figure_count')::int > 5 
                        THEN 'Medium'
                        ELSE 'Low'
                    END as impact_level,
                    COUNT(*) as count
                FROM article_metadata
                GROUP BY impact_level
            """
            )
            impact_results = db.execute(impact_sql).fetchall()

            # Research areas
            research_areas = DashboardService.get_research_areas(limit=5)

            # Methodology breakdown (section types as proxy)
            method_sql = text(
                """
                SELECT 
                    section_type,
                    COUNT(DISTINCT article_id) as article_count
                FROM article_sections
                WHERE section_type IN ('materials_and_methods', 'results', 'discussion')
                GROUP BY section_type
                ORDER BY article_count DESC
            """
            )
            method_results = db.execute(method_sql).fetchall()

            cited_articles = DashboardService.get_top_cited_articles(limit=10)

            # Top funders
            funders = DashboardService.get_top_funders(limit=10)

            # Topics distribution
            topics = DashboardService.get_topics_distribution(limit=10)

            return {
                "trends": {
                    "labels": [str(t["year"]) for t in timeline if t["year"]],
                    "publications": [t["count"] for t in timeline if t["year"]],
                    "citations": [
                        int(t["count"] * 0.3) for t in timeline if t["year"]
                    ],  # Estimated
                },
                "impact": {
                    "labels": [r.impact_level for r in impact_results],
                    "data": [r.count for r in impact_results],
                },
                "researchAreas": {
                    "labels": [ra["name"] for ra in research_areas],
                    "data": [ra["count"] for ra in research_areas],
                },
                "methodology": {
                    "labels": [
                        r.section_type.replace("_", " ").title() for r in method_results
                    ],
                    "data": [r.article_count for r in method_results],
                },
                "topCited": {
                    "labels": [a["title"][:30] + "..." for a in cited_articles],
                    "data": [a["citations"] for a in cited_articles],
                    "pmcids": [a["pmcid"] for a in cited_articles],
                },
                "topFunders": {
                    "labels": [f["abbreviation"] or f["name"] for f in funders],
                    "data": [f["publication_count"] for f in funders],
                    "fullNames": [f["name"] for f in funders],
                },
                "topicsDistribution": {
                    "labels": [t["name"] for t in topics],
                    "data": [t["count"] for t in topics],
                },
            }

    @staticmethod
    def get_top_cited_articles(limit: int = 10) -> List[Dict]:
        """Get articles with most citations"""
        with get_db() as db:
            results = (
                db.query(
                    Articles.pmcid,
                    Articles.title,
                    Articles.citations,
                    Articles.publication_date,
                    Articles.journal,
                )
                .filter(Articles.citations.isnot(None))
                .order_by(Articles.citations.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "pmcid": r.pmcid,
                    "title": r.title,
                    "citations": r.citations or 0,
                    "date": (
                        r.publication_date.isoformat() if r.publication_date else None
                    ),
                    "journal": r.journal,
                }
                for r in results
            ]

    @staticmethod
    def get_top_funders(limit: int = 10) -> List[Dict]:
        """Get funding sources with most publications"""
        with get_db() as db:
            results = (
                db.query(
                    FundingSources.name,
                    FundingSources.abbreviation,
                    FundingSources.country,
                    func.count(ArticleFunding.article_id).label("publication_count"),
                )
                .join(ArticleFunding)
                .group_by(
                    FundingSources.id,
                    FundingSources.name,
                    FundingSources.abbreviation,
                    FundingSources.country,
                )
                .order_by(desc("publication_count"))
                .limit(limit)
                .all()
            )

            return [
                {
                    "name": r.name,
                    "abbreviation": r.abbreviation,
                    "country": r.country,
                    "publication_count": r.publication_count,
                }
                for r in results
            ]

    @staticmethod
    def get_topics_distribution(limit: int = 15) -> List[Dict]:
        """Get topics with article counts"""
        with get_db() as db:
            results = (
                db.query(
                    Topics.name,
                    Topics.description,
                    func.count(ArticleTopics.article_id).label("article_count"),
                )
                .join(ArticleTopics)
                .group_by(Topics.id, Topics.name, Topics.description)
                .order_by(desc("article_count"))
                .limit(limit)
                .all()
            )

            return [
                {"name": r.name, "description": r.description, "count": r.article_count}
                for r in results
            ]


# ============================================
# AI Insights Generator Service
# ============================================


class InsightsService:
    """Generate AI-powered insights from publication data"""

    @staticmethod
    def generate_insights() -> List[Dict]:
        """Generate actionable insights from the data"""
        insights = []

        with get_db() as db:
            # Insight 1: NASA research priority gaps
            nasa_gaps = db.execute(
                text(
                    """
                SELECT 
                    k.keyword,
                    COUNT(ak.article_id) as count
                FROM keywords k
                JOIN article_keywords ak ON k.id = ak.keyword_id
                JOIN article_metadata am ON ak.article_id = am.article_id
                WHERE k.category IN ('biological_system', 'experiment_type')
                    AND am.custom_fields->'nasa_info'->>'mentions_nasa' = 'true'
                GROUP BY k.keyword
                HAVING COUNT(ak.article_id) < 5
                ORDER BY count ASC
                LIMIT 3
            """
                )
            ).fetchall()

            if nasa_gaps:
                gap_areas = ", ".join([g.keyword for g in nasa_gaps[:3]])
                insights.append(
                    {
                        "icon": "🎯",
                        "title": "Mission Planning Priority",
                        "content": f"Critical gaps identified in {gap_areas}. Recommend accelerating research in these areas before Mars missions.",
                    }
                )

            # Insight 2: Trending research areas
            recent_trends = db.execute(
                text(
                    """
                SELECT 
                    k.keyword,
                    COUNT(ak.article_id) as recent_count
                FROM keywords k
                JOIN article_keywords ak ON k.id = ak.keyword_id
                JOIN articles a ON ak.article_id = a.id
                WHERE a.publication_date >= CURRENT_DATE - INTERVAL '2 years'
                    AND k.category IN ('biological_system', 'topic')
                GROUP BY k.keyword
                ORDER BY recent_count DESC
                LIMIT 3
            """
                )
            ).fetchall()

            if recent_trends:
                top_trend = recent_trends[0].keyword
                insights.append(
                    {
                        "icon": "🌱",
                        "title": "Emerging Research Focus",
                        "content": f"Strong momentum in {top_trend} research with {recent_trends[0].recent_count} recent publications. Consider allocating additional resources to this area.",
                    }
                )

            # Insight 3: Collaboration opportunities
            collab_sql = text(
                """
                SELECT 
                    COUNT(DISTINCT aa.author_id) as unique_authors,
                    COUNT(DISTINCT aa.article_id) as total_articles,
                    COUNT(DISTINCT aa.article_id)::float / COUNT(DISTINCT aa.author_id) as articles_per_author
                FROM article_authors aa
                JOIN article_metadata am ON aa.article_id = am.article_id
                WHERE am.custom_fields->'nasa_info'->>'mentions_iss' = 'true'
            """
            )
            collab_stats = db.execute(collab_sql).fetchone()

            if collab_stats and collab_stats.articles_per_author > 1.5:
                insights.append(
                    {
                        "icon": "🔬",
                        "title": "Research Collaboration",
                        "content": f"ISS experiments show strong author collaboration ({collab_stats.unique_authors} researchers). Increase flight opportunities for high-impact biological research.",
                    }
                )

            # Insight 4: Data completeness
            metadata_quality = db.execute(
                text(
                    """
                SELECT 
                    COUNT(*) as total,
                    COUNT(doi) as has_doi,
                    COUNT(publication_date) as has_date
                FROM articles
            """
                )
            ).fetchone()

            completeness_pct = (
                (metadata_quality.has_doi + metadata_quality.has_date)
                / (metadata_quality.total * 2)
            ) * 100

            if completeness_pct < 80:
                insights.append(
                    {
                        "icon": "📊",
                        "title": "Data Quality Enhancement",
                        "content": f"Metadata completeness at {completeness_pct:.0f}%. Improving DOI and date coverage will enhance citation tracking and trend analysis.",
                    }
                )
            else:
                insights.append(
                    {
                        "icon": "📊",
                        "title": "Data Integration Excellence",
                        "content": f"High metadata quality ({completeness_pct:.0f}% complete) enables robust analytics. Cross-disciplinary studies show highest citation impact.",
                    }
                )

            # Insight 5: Organism diversity
            organism_diversity = db.execute(
                text(
                    """
                SELECT COUNT(DISTINCT organism_id) as unique_organisms
                FROM article_organisms
            """
                )
            ).scalar()

            if organism_diversity and organism_diversity > 10:
                insights.append(
                    {
                        "icon": "🧬",
                        "title": "Model Organism Diversity",
                        "content": f"Research spans {organism_diversity} different organisms, providing robust cross-species validation. Continue diversified approach for comprehensive space biology understanding.",
                    }
                )

        return insights[:4]  # Return top 4 insights


# ============================================
# Knowledge Graph Service
# ============================================


class KnowledgeGraphService:
    """Build and query knowledge graph relationships"""

    @staticmethod
    def build_keyword_network(limit: int = 50) -> Dict:
        """Build network of keywords and their co-occurrence"""
        with get_db() as db:
            # Get co-occurring keywords
            sql = text(
                """
                WITH keyword_pairs AS (
                    SELECT 
                        k1.id as keyword1_id,
                        k1.keyword as keyword1,
                        k2.id as keyword2_id,
                        k2.keyword as keyword2,
                        COUNT(DISTINCT ak1.article_id) as co_occurrence
                    FROM article_keywords ak1
                    JOIN article_keywords ak2 ON ak1.article_id = ak2.article_id
                    JOIN keywords k1 ON ak1.keyword_id = k1.id
                    JOIN keywords k2 ON ak2.keyword_id = k2.id
                    WHERE k1.id < k2.id
                        AND k1.category IN ('biological_system', 'experiment_type', 'organism')
                        AND k2.category IN ('biological_system', 'experiment_type', 'organism')
                    GROUP BY k1.id, k1.keyword, k2.id, k2.keyword
                    HAVING COUNT(DISTINCT ak1.article_id) >= 3
                    ORDER BY co_occurrence DESC
                    LIMIT :limit
                )
                SELECT * FROM keyword_pairs
            """
            )

            relationships = db.execute(sql, {"limit": limit}).fetchall()

            # Build nodes and edges
            nodes = {}
            edges = []

            for rel in relationships:
                # Add nodes
                if rel.keyword1_id not in nodes:
                    nodes[rel.keyword1_id] = {
                        "id": rel.keyword1_id,
                        "label": rel.keyword1,
                        "size": 1,
                    }
                if rel.keyword2_id not in nodes:
                    nodes[rel.keyword2_id] = {
                        "id": rel.keyword2_id,
                        "label": rel.keyword2,
                        "size": 1,
                    }

                # Increase node size based on connections
                nodes[rel.keyword1_id]["size"] += 1
                nodes[rel.keyword2_id]["size"] += 1

                # Add edge
                edges.append(
                    {
                        "source": rel.keyword1_id,
                        "target": rel.keyword2_id,
                        "weight": rel.co_occurrence,
                    }
                )

            return {"nodes": list(nodes.values()), "edges": edges}

    @staticmethod
    def get_research_clusters() -> List[Dict]:
        """Identify major research clusters"""
        with get_db() as db:
            # Group keywords by category and find highly connected ones
            sql = text(
                """
                SELECT 
                    k.category,
                    k.keyword,
                    COUNT(DISTINCT ak.article_id) as article_count,
                    ARRAY_AGG(DISTINCT k2.keyword ORDER BY k2.keyword) FILTER (
                        WHERE k2.id != k.id
                    ) as related_keywords
                FROM keywords k
                JOIN article_keywords ak ON k.id = ak.keyword_id
                LEFT JOIN article_keywords ak2 ON ak.article_id = ak2.article_id
                LEFT JOIN keywords k2 ON ak2.keyword_id = k2.id
                WHERE k.category IN ('biological_system', 'experiment_type', 'organism')
                GROUP BY k.id, k.category, k.keyword
                HAVING COUNT(DISTINCT ak.article_id) >= 5
                ORDER BY article_count DESC
                LIMIT 10
            """
            )

            results = db.execute(sql).fetchall()

            clusters = []
            for r in results:
                clusters.append(
                    {
                        "name": r.keyword.title(),
                        "category": r.category,
                        "article_count": r.article_count,
                        "related_topics": (
                            r.related_keywords[:5] if r.related_keywords else []
                        ),
                    }
                )

            return clusters

    @staticmethod
    def get_concept_relationships() -> List[Dict]:
        """Get relationships between key concepts"""
        with get_db() as db:
            # Find strongly related concept pairs
            sql = text(
                """
                SELECT 
                    k1.keyword as concept1,
                    k2.keyword as concept2,
                    COUNT(DISTINCT ak1.article_id) as shared_articles,
                    k1.category as category1,
                    k2.category as category2
                FROM article_keywords ak1
                JOIN article_keywords ak2 ON ak1.article_id = ak2.article_id
                JOIN keywords k1 ON ak1.keyword_id = k1.id
                JOIN keywords k2 ON ak2.keyword_id = k2.id
                WHERE k1.id < k2.id
                    AND k1.category IN ('biological_system', 'experiment_type')
                    AND k2.category IN ('biological_system', 'experiment_type')
                GROUP BY k1.keyword, k2.keyword, k1.category, k2.category
                HAVING COUNT(DISTINCT ak1.article_id) >= 5
                ORDER BY shared_articles DESC
                LIMIT 15
            """
            )

            results = db.execute(sql).fetchall()

            return [
                {
                    "from": r.concept1,
                    "to": r.concept2,
                    "strength": r.shared_articles,
                    "type": f"{r.category1}-{r.category2}",
                }
                for r in results
            ]

    @staticmethod
    def get_author_collaboration_network(min_collaborations: int = 2) -> Dict:
        """Build network of author collaborations"""
        with get_db() as db:
            sql = text(
                """
                WITH author_pairs AS (
                    SELECT 
                        a1.id as author1_id,
                        a1.full_name as author1,
                        a2.id as author2_id,
                        a2.full_name as author2,
                        COUNT(DISTINCT aa1.article_id) as collaborations
                    FROM article_authors aa1
                    JOIN article_authors aa2 ON aa1.article_id = aa2.article_id
                    JOIN authors a1 ON aa1.author_id = a1.id
                    JOIN authors a2 ON aa2.author_id = a2.id
                    WHERE a1.id < a2.id
                    GROUP BY a1.id, a1.full_name, a2.id, a2.full_name
                    HAVING COUNT(DISTINCT aa1.article_id) >= :min_collabs
                    ORDER BY collaborations DESC
                    LIMIT 100
                )
                SELECT * FROM author_pairs
            """
            )

            results = db.execute(sql, {"min_collabs": min_collaborations}).fetchall()

            nodes = {}
            edges = []

            for r in results:
                if r.author1_id not in nodes:
                    nodes[r.author1_id] = {
                        "id": r.author1_id,
                        "label": r.author1,
                        "type": "author",
                    }
                if r.author2_id not in nodes:
                    nodes[r.author2_id] = {
                        "id": r.author2_id,
                        "label": r.author2,
                        "type": "author",
                    }

                edges.append(
                    {
                        "source": r.author1_id,
                        "target": r.author2_id,
                        "weight": r.collaborations,
                    }
                )

            return {"nodes": list(nodes.values()), "edges": edges}


# ============================================
# Chatbot Query Service
# ============================================


class ChatbotService:
    """Specialized queries for chatbot interactions"""

    @staticmethod
    def quick_answer(question: str) -> Dict:
        """
        Attempt to answer common questions quickly
        Returns relevant articles or statistics
        """
        question_lower = question.lower()

        # Detect question type and route appropriately
        if any(
            word in question_lower
            for word in ["how many", "count", "total", "number of"]
        ):
            return ChatbotService._handle_count_question(question_lower)
        elif any(
            word in question_lower for word in ["latest", "recent", "new", "newest"]
        ):
            return ChatbotService._get_recent_articles(limit=5)
        elif any(
            word in question_lower
            for word in [
                "author",
                "researcher",
                "scientist",
                "who wrote",
                "who studied",
            ]
        ):
            return ChatbotService._handle_author_question(question_lower)
        elif any(
            word in question_lower
            for word in ["organism", "species", "animal", "plant"]
        ):
            return ChatbotService._handle_organism_question(question_lower)
        elif (
            "compare" in question_lower
            or "versus" in question_lower
            or "vs" in question_lower
        ):
            return ChatbotService._handle_comparison_question(question_lower)
        else:
            # Fallback to full-text search
            results = ArticleSearchService.full_text_search(question, limit=5)
            return {
                "answer_type": "search_results",
                "query": question,
                "results": results,
                "message": f"Found {len(results)} articles related to your question",
            }

    @staticmethod
    def _handle_count_question(question: str) -> Dict:
        """Handle counting questions"""
        metrics = DashboardService.get_overview_metrics()

        if "nasa" in question:
            return {
                "answer_type": "count",
                "count": metrics["nasa_related_count"],
                "percentage": metrics["nasa_related_percent"],
                "description": "NASA-related publications in database",
                "total": metrics["total_publications"],
            }
        elif "author" in question:
            return {
                "answer_type": "count",
                "count": metrics["total_authors"],
                "description": "Unique authors in database",
            }
        elif "keyword" in question or "topic" in question:
            return {
                "answer_type": "count",
                "count": metrics["total_keywords"],
                "description": "Unique keywords/topics identified",
            }
        else:
            return {
                "answer_type": "count",
                "count": metrics["total_publications"],
                "description": "Total publications in database",
                "recent": metrics["recent_publications"],
            }

    @staticmethod
    def _get_recent_articles(limit: int = 5) -> Dict:
        """Get most recent publications"""
        with get_db() as db:
            articles = (
                db.query(Articles)
                .filter(Articles.publication_date.isnot(None))
                .order_by(Articles.publication_date.desc())
                .limit(limit)
                .all()
            )

            return {
                "answer_type": "recent_articles",
                "count": len(articles),
                "articles": [
                    {
                        "pmcid": a.pmcid,
                        "title": a.title,
                        "date": a.publication_date.isoformat(),
                        "journal": a.journal,
                    }
                    for a in articles
                ],
            }

    @staticmethod
    def _handle_author_question(question: str) -> Dict:
        """Handle questions about authors"""
        # Extract potential author name from question
        # Simple implementation - can be enhanced with NER
        top_authors = DashboardService.get_top_authors(limit=10)

        return {
            "answer_type": "author_info",
            "top_authors": top_authors,
            "message": "Most prolific authors in the database",
        }

    @staticmethod
    def _handle_organism_question(question: str) -> Dict:
        """Handle questions about organisms"""
        organisms = DashboardService.get_organisms_studied(limit=10)

        return {
            "answer_type": "organism_info",
            "organisms": organisms,
            "message": "Most studied organisms in NASA bioscience research",
        }

    @staticmethod
    def _handle_comparison_question(question: str) -> Dict:
        """Handle comparison questions"""
        # Extract topics being compared (simplified)
        words = question.split()

        # Try to find topics in question
        topics = []
        for i, word in enumerate(words):
            if word.lower() in ["compare", "versus", "vs", "and"]:
                if i > 0:
                    topics.append(words[i - 1])
                if i < len(words) - 1:
                    topics.append(words[i + 1])

        if len(topics) >= 2:
            # Search for each topic
            results = {}
            for topic in topics[:2]:
                topic_results = ArticleSearchService.full_text_search(topic, limit=3)
                results[topic] = len(topic_results)

            return {
                "answer_type": "comparison",
                "topics": topics[:2],
                "results": results,
                "message": f"Comparison of research coverage",
            }

        return {
            "answer_type": "clarification_needed",
            "message": "Please specify the two topics you want to compare",
        }

    @staticmethod
    def _search_by_topic(question: str) -> Dict:
        """Search for articles related to a topic mentioned in question"""
        results = ArticleSearchService.full_text_search(question, limit=5)
        return {
            "answer_type": "topic_search",
            "results": results,
            "count": len(results),
        }

    @staticmethod
    def get_contextual_suggestions(user_query: str) -> List[str]:
        """Suggest follow-up queries based on user's question"""
        suggestions = []
        query_lower = user_query.lower()

        if "bone" in query_lower:
            suggestions = [
                "What organisms were studied for bone research?",
                "Show me recent bone loss publications",
                "How is bone research related to microgravity?",
            ]
        elif "radiation" in query_lower:
            suggestions = [
                "What are the health effects of space radiation?",
                "Show me radiation countermeasure research",
                "Compare radiation studies with other health research",
            ]
        elif "plant" in query_lower:
            suggestions = [
                "What plants have been studied in space?",
                "Show me recent space agriculture research",
                "How does microgravity affect plant growth?",
            ]
        else:
            suggestions = [
                "What are the main research areas?",
                "Show me NASA-related publications",
                "What are the knowledge gaps in space biology?",
            ]

        return suggestions


# ============================================
# Export Service (for reports/downloads)
# ============================================


class ExportService:
    """Generate exports and reports"""

    @staticmethod
    def generate_summary_report() -> Dict:
        """Generate a comprehensive summary report"""
        metrics = DashboardService.get_overview_metrics()
        research_areas = DashboardService.get_research_areas(limit=10)
        gaps = DashboardService.get_knowledge_gaps()
        top_authors = DashboardService.get_top_authors(limit=10)
        organisms = DashboardService.get_organisms_studied(limit=10)

        return {
            "generated_at": datetime.now().isoformat(),
            "overview": metrics,
            "top_research_areas": research_areas,
            "knowledge_gaps": gaps,
            "leading_researchers": top_authors,
            "model_organisms": organisms,
        }

    @staticmethod
    def get_article_list(filters: Dict = None) -> List[Dict]:
        """Get simplified article list for export"""
        with get_db() as db:
            query = db.query(
                Articles.pmcid,
                Articles.title,
                Articles.publication_date,
                Articles.journal,
                Articles.doi,
            )

            if filters:
                if filters.get("year"):
                    query = query.filter(
                        func.extract("year", Articles.publication_date)
                        == filters["year"]
                    )
                if filters.get("nasa_only"):
                    query = query.join(ArticleMetadata).filter(
                        ArticleMetadata.custom_fields["nasa_info"][
                            "mentions_nasa"
                        ].astext.cast(bool)
                        == True
                    )

            results = query.all()

            return [
                {
                    "pmcid": r.pmcid,
                    "title": r.title,
                    "publication_date": (
                        r.publication_date.isoformat() if r.publication_date else None
                    ),
                    "journal": r.journal,
                    "doi": r.doi,
                }
                for r in results
            ]


# ============================================
# Example Usage & Testing
# ============================================

if __name__ == "__main__":
    print("NASA Bioscience Service Layer - Complete\n")
    print("=" * 60)

    # Test 1: Overview Metrics
    print("\n1. Dashboard Metrics:")
    metrics = DashboardService.get_overview_metrics()
    print(f"   Total Publications: {metrics['total_publications']}")
    print(
        f"   NASA-Related: {metrics['nasa_related_count']} ({metrics['nasa_related_percent']}%)"
    )

    # Test 2: Research Areas
    print("\n2. Top Research Areas:")
    areas = DashboardService.get_research_areas(limit=5)
    for area in areas:
        print(f"   - {area['name']}: {area['count']} publications")

    # Test 3: Knowledge Gaps
    print("\n3. Knowledge Gaps:")
    gaps = DashboardService.get_knowledge_gaps()
    for gap in gaps[:3]:
        print(
            f"   - {gap['area']}: {gap['publication_count']} pubs ({gap['severity']})"
        )

    # Test 4: AI Insights
    print("\n4. AI-Generated Insights:")
    insights = InsightsService.generate_insights()
    for insight in insights:
        print(f"   {insight['icon']} {insight['title']}")
        print(f"      {insight['content'][:80]}...")

    # Test 5: Knowledge Graph
    print("\n5. Knowledge Graph:")
    clusters = KnowledgeGraphService.get_research_clusters()
    print(f"   Identified {len(clusters)} major research clusters")

    # Test 6: Search
    print("\n6. Article Search:")
    results = ArticleSearchService.full_text_search("bone mineralization", limit=3)
    print(f"   Found {len(results)} articles")

    # Test 7: Chatbot
    print("\n7. Chatbot Interaction:")
    answer = ChatbotService.quick_answer("How many NASA publications are there?")
    print(f"   Answer: {answer}")

    print("\n" + "=" * 60)
    print("All services operational!")
    print("\nAvailable Services:")
    print("  - UserService (chat history)")
    print("  - ArticleSearchService (full-text, keyword, filter)")
    print("  - ArticleDetailService (full article, related)")
    print("  - DashboardService (metrics, analytics, gaps)")
    print("  - InsightsService (AI-generated insights)")
    print("  - KnowledgeGraphService (networks, clusters)")
    print("  - ChatbotService (natural language Q&A)")
    print("  - ExportService (reports, downloads)")
