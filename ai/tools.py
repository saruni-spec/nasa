"""
NASA Bioscience AI Agent Tools
Enables the agent to search publications, analyze research, and provide insights
"""

from langchain_core.tools import tool
from typing import List

import sys

sys.path.append("..")
from db.service import (
    ArticleSearchService,
    ArticleDetailService,
    DashboardService,
    InsightsService,
    KnowledgeGraphService,
    ChatbotService,
)


@tool
def search_publications(query: str, limit: int = 10) -> str:
    """
    Search NASA bioscience publications using full-text search.

    Args:
        query: Search query (e.g., "bone loss microgravity", "plant growth ISS")
        limit: Maximum number of results to return (default: 10)

    Returns:
        Formatted search results with article titles, relevance scores, and snippets

    Use this when users ask to:
    - Find publications about a specific topic
    - Search for research on a particular subject
    - Look up articles related to keywords
    """
    try:
        results = ArticleSearchService.full_text_search(query=query, limit=limit)

        if not results:
            return f"No publications found matching '{query}'"

        output = [f"Found {len(results)} publications matching '{query}':\n"]

        for i, article in enumerate(results, 1):
            output.append(f"\n{i}. {article['title']}")
            output.append(f"   PMCID: {article['pmcid']}")
            output.append(f"   Journal: {article['journal'] or 'N/A'}")
            output.append(f"   Date: {article['publication_date'] or 'N/A'}")
            output.append(f"   Relevance: {article['relevance_score']:.2f}")
            output.append(f"   Section: {article['section']}")
            if article.get("keywords"):
                output.append(f"   Keywords: {', '.join(article['keywords'][:5])}")
            output.append(f"   Snippet: {article['snippet'][:200]}...")

        return "\n".join(output)

    except Exception as e:
        return f"Error searching publications: {str(e)}"


@tool
def get_article_details(pmcid: str) -> str:
    """
    Get complete details for a specific publication by PMCID.

    Args:
        pmcid: PubMed Central ID (e.g., "PMC8234567")

    Returns:
        Full article details including authors, sections, keywords, and organisms

    Use this when users ask for:
    - Details about a specific article
    - Full information on a publication
    - Authors or methods of a particular study
    """
    try:
        from db.service import get_db
        from db.models import Articles

        with get_db() as db:
            article = db.query(Articles).filter(Articles.pmcid == pmcid).first()
            if not article:
                return f"Article with PMCID {pmcid} not found"

            details = ArticleDetailService.get_article_full(article.id)

        if not details:
            return f"Could not retrieve details for {pmcid}"

        output = [f"Article Details for {pmcid}:\n"]
        output.append(f"Title: {details['title']}")
        output.append(f"Journal: {details['journal'] or 'N/A'}")
        output.append(f"Date: {details['publication_date'] or 'N/A'}")
        output.append(f"DOI: {details['doi'] or 'N/A'}")

        if details["authors"]:
            output.append(f"\nAuthors ({len(details['authors'])}):")
            for author in details["authors"][:10]:  # Show first 10
                output.append(f"  - {author['name']}")

        if details["keywords"]:
            output.append(f"\nKeywords ({len(details['keywords'])}):")
            for kw in details["keywords"][:15]:
                output.append(
                    f"  - {kw['keyword']} ({kw['category']}) - Relevance: {kw['relevance']:.2f}"
                )

        if details["organisms"]:
            output.append(f"\nOrganisms Studied:")
            for org in details["organisms"]:
                output.append(f"  - {org['scientific_name']} ({org['common_name']})")

        if details["sections"]:
            output.append(
                f"\nAvailable Sections: {', '.join([s['type'] for s in details['sections']])}"
            )

        return "\n".join(output)

    except Exception as e:
        return f"Error retrieving article details: {str(e)}"


@tool
def get_research_overview() -> str:
    """
    Get comprehensive overview of NASA bioscience research metrics.

    Returns:
        Summary of total publications, research areas, NASA involvement, and trends

    Use this when users ask:
    - "What's the overview of NASA research?"
    - "How many publications are there?"
    - "What's the state of NASA bioscience research?"
    - "Give me an overview"
    """
    try:
        metrics = DashboardService.get_overview_metrics()
        research_areas = DashboardService.get_research_areas(limit=10)

        output = ["NASA Bioscience Research Overview:\n"]
        output.append(f"📊 Total Publications: {metrics['total_publications']}")
        output.append(
            f"🚀 NASA-Related: {metrics['nasa_related_count']} ({metrics['nasa_related_percent']}%)"
        )
        output.append(f"👥 Total Authors: {metrics['total_authors']}")
        output.append(f"🔬 Research Keywords: {metrics['total_keywords']}")
        output.append(f"📅 Years of Publication: {metrics['years_of_publication']}")
        output.append(
            f"📈 Recent Publications (2 years): {metrics['recent_publications']}"
        )

        output.append("\n🔝 Top Research Areas:")
        for i, area in enumerate(research_areas, 1):
            output.append(f"  {i}. {area['name']} - {area['count']} publications")

        return "\n".join(output)

    except Exception as e:
        return f"Error getting research overview: {str(e)}"


@tool
def identify_knowledge_gaps() -> str:
    """
    Identify understudied areas and research gaps in NASA bioscience.

    Returns:
        List of research areas with low publication counts that need more study

    Use this when users ask:
    - "What are the knowledge gaps?"
    - "What areas need more research?"
    - "Where should we focus future studies?"
    - "What's understudied?"
    """
    try:
        gaps = DashboardService.get_knowledge_gaps()

        output = ["Critical Knowledge Gaps in NASA Bioscience:\n"]

        for i, gap in enumerate(gaps, 1):
            output.append(f"{i}. {gap['area']} ({gap['category']})")
            output.append(f"   Severity: {gap['severity']}")
            output.append(f"   Publications: {gap['publication_count']}")
            output.append(f"   Progress: {gap['progress']}% of expected coverage\n")

        output.append(
            "\nRecommendation: These areas have fewer than 10 publications and represent "
        )
        output.append(
            "opportunities for future research investment and mission planning."
        )

        return "\n".join(output)

    except Exception as e:
        return f"Error identifying knowledge gaps: {str(e)}"


@tool
def generate_research_insights() -> str:
    """
    Generate AI-powered insights from publication analysis.

    Returns:
        Strategic insights and recommendations based on research patterns

    Use this when users ask:
    - "What are the key insights?"
    - "What patterns do you see in the research?"
    - "What should mission planners know?"
    - "Give me strategic recommendations"
    """
    try:
        insights = InsightsService.generate_insights()

        output = ["AI-Generated Research Insights:\n"]

        for i, insight in enumerate(insights, 1):
            output.append(f"{insight['icon']} {insight['title']}")
            output.append(f"   {insight['content']}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error generating insights: {str(e)}"


@tool
def find_related_articles(pmcid: str, limit: int = 5) -> str:
    """
    Find articles related to a specific publication based on shared keywords.

    Args:
        pmcid: PubMed Central ID of the reference article
        limit: Maximum number of related articles to return

    Returns:
        List of related publications with similarity scores

    Use this when users ask:
    - "What articles are related to this one?"
    - "Find similar research"
    - "What else has been studied on this topic?"
    """
    try:
        from db.service import get_db
        from db.models import Articles

        with get_db() as db:
            article = db.query(Articles).filter(Articles.pmcid == pmcid).first()
            if not article:
                return f"Article with PMCID {pmcid} not found"

            related = ArticleDetailService.get_related_articles(article.id, limit=limit)

        if not related:
            return f"No related articles found for {pmcid}"

        output = [f"Articles Related to {pmcid}:\n"]

        for i, rel in enumerate(related, 1):
            output.append(f"{i}. {rel['title']}")
            output.append(f"   PMCID: {rel['pmcid']}")
            output.append(f"   Date: {rel['publication_date'] or 'N/A'}")
            output.append(f"   Shared Keywords: {rel['shared_keywords']}")
            output.append(f"   Similarity Score: {rel['similarity_score']:.2f}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error finding related articles: {str(e)}"


@tool
def get_top_authors(limit: int = 10) -> str:
    """
    Get the most prolific authors in NASA bioscience research.

    Args:
        limit: Number of top authors to return (default: 10)

    Returns:
        List of authors ranked by publication count

    Use this when users ask:
    - "Who are the leading researchers?"
    - "Which authors publish the most?"
    - "Who are the key scientists?"
    """
    try:
        authors = DashboardService.get_top_authors(limit=limit)

        output = [f"Top {limit} Authors in NASA Bioscience:\n"]

        for i, author in enumerate(authors, 1):
            output.append(f"{i}. {author['author']}")
            output.append(f"   Publications: {author['publication_count']}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error retrieving top authors: {str(e)}"


@tool
def get_organisms_studied(limit: int = 10) -> str:
    """
    Get the most studied organisms in NASA bioscience research.

    Args:
        limit: Number of organisms to return (default: 10)

    Returns:
        List of organisms ranked by number of studies

    Use this when users ask:
    - "What organisms are studied?"
    - "Which species are used in research?"
    - "What model organisms does NASA use?"
    """
    try:
        organisms = DashboardService.get_organisms_studied(limit=limit)

        output = [f"Top {limit} Organisms Studied:\n"]

        for i, org in enumerate(organisms, 1):
            output.append(f"{i}. {org['organism']}")
            if org["common_name"]:
                output.append(f"   Common Name: {org['common_name']}")
            output.append(f"   Studies: {org['study_count']}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error retrieving organisms: {str(e)}"


@tool
def analyze_research_trends() -> str:
    """
    Analyze publication trends over time and identify emerging areas.

    Returns:
        Analysis of publication trends, growth areas, and temporal patterns

    Use this when users ask:
    - "What are the trends?"
    - "How has research evolved over time?"
    - "What's trending in NASA research?"
    - "Show me publication trends"
    """
    try:
        timeline = DashboardService.get_publication_timeline()
        research_areas = DashboardService.get_research_areas(limit=5)

        output = ["Research Trend Analysis:\n"]
        output.append("📈 Publications by Year:")

        # Show recent years
        recent_years = [t for t in timeline if t["year"] and t["year"] >= 2015]
        for entry in recent_years[-10:]:  # Last 10 years
            output.append(f"   {entry['year']}: {entry['count']} publications")

        # Calculate growth
        if len(recent_years) >= 2:
            growth = recent_years[-1]["count"] - recent_years[-2]["count"]
            growth_pct = (
                (growth / recent_years[-2]["count"]) * 100
                if recent_years[-2]["count"] > 0
                else 0
            )
            output.append(
                f"\n📊 Year-over-Year Growth: {growth:+d} publications ({growth_pct:+.1f}%)"
            )

        output.append("\n🔥 Hot Research Areas:")
        for area in research_areas:
            output.append(f"   • {area['name']}: {area['count']} publications")

        return "\n".join(output)

    except Exception as e:
        return f"Error analyzing trends: {str(e)}"


@tool
def get_knowledge_graph_clusters() -> str:
    """
    Get major research clusters and their relationships.

    Returns:
        Research clusters showing interconnected topics and concepts

    Use this when users ask:
    - "What are the research clusters?"
    - "How are topics connected?"
    - "Show me the knowledge graph"
    - "What research areas are related?"
    """
    try:
        clusters = KnowledgeGraphService.get_research_clusters()
        relationships = KnowledgeGraphService.get_concept_relationships()

        output = ["Research Knowledge Clusters:\n"]

        for i, cluster in enumerate(clusters, 1):
            output.append(f"{i}. {cluster['name']} ({cluster['category']})")
            output.append(f"   Publications: {cluster['article_count']}")
            if cluster.get("related_topics"):
                output.append(f"   Related: {', '.join(cluster['related_topics'][:3])}")
            output.append("")

        output.append("\n🔗 Strong Concept Relationships:")
        for i, rel in enumerate(relationships[:5], 1):
            output.append(f"{i}. {rel['from']} ↔ {rel['to']}")
            output.append(f"   Strength: {rel['strength']} shared publications\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error retrieving knowledge graph: {str(e)}"


@tool
def search_by_keywords(keywords: List[str], min_relevance: float = 0.5) -> str:
    """
    Search for publications by specific keywords.

    Args:
        keywords: List of keywords to search for
        min_relevance: Minimum relevance score (0.0 to 1.0)

    Returns:
        Articles matching the specified keywords

    Use this when users provide:
    - Specific keywords or tags
    - Multiple search terms
    - Precise topic identifiers
    """
    try:
        results = ArticleSearchService.search_by_keywords(
            keywords=keywords, min_relevance=min_relevance, limit=10
        )

        if not results:
            return f"No publications found with keywords: {', '.join(keywords)}"

        output = [f"Publications matching keywords {', '.join(keywords)}:\n"]

        for i, article in enumerate(results, 1):
            output.append(f"{i}. {article['title']}")
            output.append(f"   PMCID: {article['pmcid']}")
            output.append(f"   Date: {article['publication_date'] or 'N/A'}")
            output.append(f"   Matched: {', '.join(article['matched_keywords'])}")
            output.append(f"   Relevance: {article['relevance_score']:.2f}\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error searching by keywords: {str(e)}"


@tool
def quick_answer(question: str) -> str:
    """
    Get quick answers to common questions using specialized queries.

    Args:
        question: Natural language question

    Returns:
        Direct answer with relevant data

    Use this for:
    - Count questions ("How many...")
    - Recent queries ("What's new...")
    - Comparison questions ("Compare X and Y")
    - Author questions ("Who studied...")
    """
    try:
        answer = ChatbotService.quick_answer(question)

        answer_type = answer.get("answer_type")

        if answer_type == "count":
            output = [f"Answer: {answer['count']}"]
            output.append(f"Description: {answer['description']}")
            if answer.get("percentage"):
                output.append(f"Percentage: {answer['percentage']}%")
            if answer.get("total"):
                output.append(f"Out of {answer['total']} total")
            return "\n".join(output)

        elif answer_type == "recent_articles":
            output = [f"Most Recent {answer['count']} Publications:\n"]
            for article in answer["articles"]:
                output.append(f"• {article['title']}")
                output.append(f"  {article['date']} - {article['journal']}\n")
            return "\n".join(output)

        elif answer_type == "search_results":
            if answer["results"]:
                output = [answer["message"] + "\n"]
                for i, result in enumerate(answer["results"][:5], 1):
                    output.append(f"{i}. {result['title']}")
                    output.append(f"   Relevance: {result['relevance_score']:.2f}\n")
                return "\n".join(output)
            return f"No results found for: {answer['query']}"

        else:
            return str(answer.get("message", "Unable to process question"))

    except Exception as e:
        return f"Error answering question: {str(e)}"


all_tools = [
    search_publications,
    get_article_details,
    get_research_overview,
    identify_knowledge_gaps,
    generate_research_insights,
    find_related_articles,
    get_top_authors,
    get_organisms_studied,
    analyze_research_trends,
    get_knowledge_graph_clusters,
    search_by_keywords,
    quick_answer,
]
