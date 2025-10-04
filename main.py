"""
FastAPI Routes for NASA Bioscience Dashboard
Maps frontend API endpoints to service layer
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import logging

# Import service layer
from db.service import (
    DashboardService,
    ArticleSearchService,
    ArticleDetailService,
    InsightsService,
    KnowledgeGraphService,
    ExportService,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NASA Bioscience Publications API",
    description="API for exploring NASA bioscience research publications",
    version="1.0.0",
)

# CORS middleware (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Request/Response Models
# ============================================


class MetricsResponse(BaseModel):
    total_publications: int
    publications_with_doi: int
    doi_coverage_percent: float
    total_authors: int
    total_keywords: int
    nasa_related_count: int
    nasa_related_percent: float
    recent_publications: int


class ResearchArea(BaseModel):
    name: str
    count: int
    category: Optional[str] = None


class KnowledgeGap(BaseModel):
    area: str
    category: str
    publication_count: int
    severity: str
    progress: int


class Insight(BaseModel):
    icon: str
    title: str
    content: str


class SearchFilters(BaseModel):
    nasa_related: Optional[bool] = None
    organisms: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    has_doi: Optional[bool] = None


class ArticleSummary(BaseModel):
    article_id: int
    pmcid: str
    title: str
    publication_date: Optional[str]
    journal: Optional[str]
    doi: Optional[str]


class SearchResult(BaseModel):
    article_id: int
    pmcid: str
    title: str
    publication_date: Optional[str]
    journal: Optional[str]
    section: str
    relevance_score: float
    snippet: str


# ============================================
# Dashboard Routes
# ============================================

templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root(request: Request):
    """Landing page endpoint."""

    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    Get overview metrics for dashboard

    Returns:
        - Total publications
        - NASA-related percentage
        - Author count
        - Keyword count
        - Recent publications
    """
    try:
        metrics = DashboardService.get_overview_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching metrics")


@app.get("/api/research-areas", response_model=List[ResearchArea])
async def get_research_areas(limit: int = Query(10, ge=1, le=50)):
    """
    Get top research areas by publication count

    Args:
        limit: Number of research areas to return (default: 10)
    """
    try:
        areas = DashboardService.get_research_areas(limit=limit)
        return areas
    except Exception as e:
        logger.error(f"Error fetching research areas: {e}")
        raise HTTPException(status_code=500, detail="Error fetching research areas")


@app.get("/api/knowledge-gaps", response_model=List[KnowledgeGap])
async def get_knowledge_gaps():
    """
    Get understudied research areas that need attention

    Returns knowledge gaps with severity ratings and progress percentages
    """
    try:
        gaps = DashboardService.get_knowledge_gaps()
        return gaps
    except Exception as e:
        logger.error(f"Error fetching knowledge gaps: {e}")
        raise HTTPException(status_code=500, detail="Error fetching knowledge gaps")


@app.get("/api/insights", response_model=List[Insight])
async def get_insights():
    """
    Get AI-generated insights from publication analysis

    Returns actionable insights for mission planning and research priorities
    """
    try:
        insights = InsightsService.generate_insights()
        return insights
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail="Error generating insights")


@app.get("/api/analytics")
async def get_analytics():
    """
    Get comprehensive analytics data for charts

    Returns:
        - Publication trends over time
        - Impact distribution
        - Research area breakdown
        - Methodology distribution
    """
    try:
        analytics = DashboardService.get_analytics_breakdown()
        return analytics
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching analytics")


@app.get("/api/timeline")
async def get_publication_timeline():
    """Get publications by year for timeline visualization"""
    try:
        timeline = DashboardService.get_publication_timeline()
        return {"timeline": timeline}
    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
        raise HTTPException(status_code=500, detail="Error fetching timeline")


@app.get("/api/top-authors")
async def get_top_authors(limit: int = Query(20, ge=1, le=100)):
    """
    Get most prolific authors

    Args:
        limit: Number of authors to return (default: 20)
    """
    try:
        authors = DashboardService.get_top_authors(limit=limit)
        return {"authors": authors}
    except Exception as e:
        logger.error(f"Error fetching top authors: {e}")
        raise HTTPException(status_code=500, detail="Error fetching top authors")


@app.get("/api/organisms")
async def get_organisms_studied(limit: int = Query(15, ge=1, le=50)):
    """
    Get most studied organisms

    Args:
        limit: Number of organisms to return (default: 15)
    """
    try:
        organisms = DashboardService.get_organisms_studied(limit=limit)
        return {"organisms": organisms}
    except Exception as e:
        logger.error(f"Error fetching organisms: {e}")
        raise HTTPException(status_code=500, detail="Error fetching organisms")


# ============================================
# Search & Publications Routes
# ============================================


@app.get("/api/search", response_model=List[SearchResult])
async def search_publications(
    q: str = Query(..., min_length=2, description="Search query"),
    section: Optional[str] = Query(None, description="Filter by section type"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Full-text search across publications

    Args:
        q: Search query
        section: Optional section filter (abstract, results, conclusions, etc.)
        limit: Maximum results to return
    """
    try:
        section_filter = [section] if section else None
        results = ArticleSearchService.full_text_search(
            query=q, section_types=section_filter, limit=limit
        )
        return results
    except Exception as e:
        logger.error(f"Error searching publications: {e}")
        raise HTTPException(status_code=500, detail="Error searching publications")


@app.post("/api/publications", response_model=dict)
async def filter_publications(
    filters: SearchFilters,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Filter publications by multiple criteria

    Args:
        filters: SearchFilters object with optional filters
        limit: Maximum results per page
        offset: Pagination offset
    """
    try:
        date_from = (
            datetime.fromisoformat(filters.date_from) if filters.date_from else None
        )
        date_to = datetime.fromisoformat(filters.date_to) if filters.date_to else None

        results = ArticleSearchService.filter_articles(
            nasa_related=filters.nasa_related,
            organisms=filters.organisms,
            date_from=date_from,
            date_to=date_to,
            has_doi=filters.has_doi,
            limit=limit,
            offset=offset,
        )
        return results
    except Exception as e:
        logger.error(f"Error filtering publications: {e}")
        raise HTTPException(status_code=500, detail="Error filtering publications")


@app.get("/api/publications/{article_id}")
async def get_article_details(article_id: int):
    """
    Get complete details for a specific article

    Args:
        article_id: Article database ID
    """
    try:
        article = ArticleDetailService.get_article_full(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching article details: {e}")
        raise HTTPException(status_code=500, detail="Error fetching article details")


@app.get("/api/publications/{article_id}/related")
async def get_related_articles(article_id: int, limit: int = Query(10, ge=1, le=50)):
    """
    Get articles related to a specific article

    Args:
        article_id: Article database ID
        limit: Maximum related articles to return
    """
    try:
        related = ArticleDetailService.get_related_articles(article_id, limit=limit)
        return {"article_id": article_id, "related_articles": related}
    except Exception as e:
        logger.error(f"Error fetching related articles: {e}")
        raise HTTPException(status_code=500, detail="Error fetching related articles")


# ============================================
# Knowledge Graph Routes
# ============================================


@app.get("/api/knowledge-graph")
async def get_knowledge_graph(limit: int = Query(50, ge=10, le=200)):
    """
    Get knowledge graph network data

    Returns nodes and edges for keyword co-occurrence network

    Args:
        limit: Maximum number of relationships to include
    """
    try:
        graph = KnowledgeGraphService.build_keyword_network(limit=limit)
        return graph
    except Exception as e:
        logger.error(f"Error building knowledge graph: {e}")
        raise HTTPException(status_code=500, detail="Error building knowledge graph")


@app.get("/api/knowledge-graph/clusters")
async def get_research_clusters():
    """Get major research clusters identified in the literature"""
    try:
        clusters = KnowledgeGraphService.get_research_clusters()
        return {"clusters": clusters}
    except Exception as e:
        logger.error(f"Error fetching research clusters: {e}")
        raise HTTPException(status_code=500, detail="Error fetching research clusters")


@app.get("/api/knowledge-graph/relationships")
async def get_concept_relationships():
    """Get relationships between key research concepts"""
    try:
        relationships = KnowledgeGraphService.get_concept_relationships()
        return {"relationships": relationships}
    except Exception as e:
        logger.error(f"Error fetching concept relationships: {e}")
        raise HTTPException(status_code=500, detail="Error fetching relationships")


@app.get("/api/knowledge-graph/authors")
async def get_author_network(min_collaborations: int = Query(2, ge=1, le=10)):
    """
    Get author collaboration network

    Args:
        min_collaborations: Minimum number of joint publications to include
    """
    try:
        network = KnowledgeGraphService.get_author_collaboration_network(
            min_collaborations=min_collaborations
        )
        return network
    except Exception as e:
        logger.error(f"Error fetching author network: {e}")
        raise HTTPException(status_code=500, detail="Error fetching author network")


# ============================================
# Export Routes
# ============================================


@app.get("/api/export/summary")
async def export_summary_report():
    """Generate and export comprehensive summary report"""
    try:
        report = ExportService.generate_summary_report()
        return report
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail="Error generating report")


@app.get("/api/export/articles")
async def export_article_list(
    year: Optional[int] = Query(None, description="Filter by publication year"),
    nasa_only: bool = Query(False, description="Only NASA-related articles"),
):
    """
    Export article list with optional filters

    Args:
        year: Optional year filter
        nasa_only: If True, only return NASA-related articles
    """
    try:
        filters = {}
        if year:
            filters["year"] = year
        if nasa_only:
            filters["nasa_only"] = True

        articles = ExportService.get_article_list(filters if filters else None)
        return {"count": len(articles), "articles": articles}
    except Exception as e:
        logger.error(f"Error exporting articles: {e}")
        raise HTTPException(status_code=500, detail="Error exporting articles")


# ============================================
# Health & Status Routes
# ============================================


@app.get("/api/health")
async def health_check():
    """API health check endpoint"""
    try:
        # Quick database check
        metrics = DashboardService.get_overview_metrics()
        return {
            "status": "healthy",
            "database": "connected",
            "total_publications": metrics["total_publications"],
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/api/stats")
async def get_statistics():
    """Get quick statistics for API monitoring"""
    try:
        metrics = DashboardService.get_overview_metrics()
        return {
            "publications": {
                "total": metrics["total_publications"],
                "nasa_related": metrics["nasa_related_count"],
                "recent": metrics["recent_publications"],
            },
            "coverage": {
                "doi_percent": metrics["doi_coverage_percent"],
                "nasa_percent": metrics["nasa_related_percent"],
            },
            "entities": {
                "authors": metrics["total_authors"],
                "keywords": metrics["total_keywords"],
            },
        }
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching statistics")


# ============================================
# Error Handlers
# ============================================


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Resource not found", "path": str(request.url)}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error on {request.url}: {exc}")
    return {"error": "Internal server error", "message": "An unexpected error occurred"}


# ============================================
# Run Application
# ============================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Disable in production
        log_level="info",
    )
