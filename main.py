"""
FastAPI Routes for NASA Bioscience Dashboard - Server-Side Rendering
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import logging
import json

# Import service layer
from db.service import (
    DashboardService,
    ArticleSearchService,
    ArticleDetailService,
    InsightsService,
    KnowledgeGraphService,
    ExportService,
)
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NASA Bioscience Publications API",
    description="API for exploring NASA bioscience research publications",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

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
    years_of_publication: int


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
# Main Dashboard Route - SERVER RENDERED
# ============================================


@app.get("/")
async def root(request: Request):
    """
    Server-rendered landing page with all dashboard data pre-loaded
    """
    try:
        # Fetch all dashboard data server-side
        metrics = DashboardService.get_overview_metrics()
        research_areas = DashboardService.get_research_areas(limit=10)
        knowledge_gaps = DashboardService.get_knowledge_gaps()
        insights = InsightsService.generate_insights()
        analytics = DashboardService.get_analytics_breakdown()

        # Convert data to JSON for embedding in template
        context = {
            "request": request,
            "metrics": metrics,
            "research_areas": research_areas,
            "knowledge_gaps": knowledge_gaps,
            "insights": insights,
            "analytics": analytics,
            # Pass as JSON string for JavaScript consumption if needed
            "metrics_json": json.dumps(metrics),
            "research_areas_json": json.dumps(research_areas),
            "knowledge_gaps_json": json.dumps(knowledge_gaps),
            "insights_json": json.dumps(insights),
            "analytics_json": json.dumps(analytics),
        }

        return templates.TemplateResponse("index.html", context)

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        # Return error page
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Failed to load dashboard data",
                "metrics": {},
                "research_areas": [],
                "knowledge_gaps": [],
                "insights": [],
                "analytics": {},
            },
        )


# ============================================
# API Routes (for dynamic updates only)
# ============================================


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get overview metrics (for dynamic updates)"""
    try:
        metrics = DashboardService.get_overview_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching metrics")


@app.get("/api/research-areas", response_model=List[ResearchArea])
async def get_research_areas(limit: int = Query(10, ge=1, le=50)):
    """Get top research areas"""
    try:
        areas = DashboardService.get_research_areas(limit=limit)
        return areas
    except Exception as e:
        logger.error(f"Error fetching research areas: {e}")
        raise HTTPException(status_code=500, detail="Error fetching research areas")


@app.get("/api/knowledge-gaps", response_model=List[KnowledgeGap])
async def get_knowledge_gaps():
    """Get understudied research areas"""
    try:
        gaps = DashboardService.get_knowledge_gaps()
        return gaps
    except Exception as e:
        logger.error(f"Error fetching knowledge gaps: {e}")
        raise HTTPException(status_code=500, detail="Error fetching knowledge gaps")


@app.get("/api/insights", response_model=List[Insight])
async def get_insights():
    """Get AI-generated insights"""
    try:
        insights = InsightsService.generate_insights()
        return insights
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail="Error generating insights")


@app.get("/api/analytics")
async def get_analytics():
    """Get comprehensive analytics data"""
    try:
        analytics = DashboardService.get_analytics_breakdown()
        return analytics
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail="Error fetching analytics")


# ============================================
# Search & Publications Routes
# ============================================


@app.get("/api/search", response_model=List[SearchResult])
async def search_publications(
    q: str = Query(..., min_length=2),
    section: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """Full-text search across publications"""
    try:
        section_filter = [section] if section else None
        results = ArticleSearchService.full_text_search(
            query=q, section_types=section_filter, limit=limit
        )
        return results
    except Exception as e:
        logger.error(f"Error searching publications: {e}")
        raise HTTPException(status_code=500, detail="Error searching publications")


@app.post("/api/publications")
async def filter_publications(
    filters: SearchFilters,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Filter publications by criteria"""
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
    """Get complete details for a specific article"""
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


# ============================================
# Knowledge Graph Routes
# ============================================


@app.get("/api/knowledge-graph")
async def get_knowledge_graph(limit: int = Query(50, ge=10, le=200)):
    """Get knowledge graph network data"""
    try:
        graph = KnowledgeGraphService.build_keyword_network(limit=limit)
        return graph
    except Exception as e:
        logger.error(f"Error building knowledge graph: {e}")
        raise HTTPException(status_code=500, detail="Error building knowledge graph")


# Add at the top with other imports
from ai.agent import NasaAgent
import os

# Add after app initialization
nasa_agent = None


@app.on_event("startup")
async def startup_event():
    """Initialize the NASA agent on startup"""
    global nasa_agent
    try:
        nasa_agent = NasaAgent()
        logger.info("NASA Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize NASA Agent: {e}")


# Add new chatbot endpoint
@app.post("/api/chatbot")
async def chatbot_message(request: Request):
    """
    Handle chatbot messages
    """
    try:
        data = await request.json()
        message = data.get("message", "").strip()

        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        if not nasa_agent:
            raise HTTPException(status_code=503, detail="Agent not initialized")

        # For now, create a simple user object (you'll replace this with actual user management)
        # Placeholder user - adapt based on your User model
        class SimpleUser:
            def __init__(self):
                self.id = 1  # Default user ID
                self.name = "Guest"

        user = SimpleUser()

        # Process message through agent
        result = nasa_agent.process_message_sync(user=user, message=message)

        if result["status"] == "success":
            return {"response": result["response"], "status": "success"}
        else:
            return {
                "response": "I'm having trouble processing that right now. Please try again.",
                "status": "error",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        raise HTTPException(status_code=500, detail="Error processing message")


# ============================================
# Health Check
# ============================================


@app.get("/api/health")
async def health_check():
    """API health check endpoint"""
    try:
        metrics = DashboardService.get_overview_metrics()
        return {
            "status": "healthy",
            "database": "connected",
            "total_publications": metrics["total_publications"],
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
