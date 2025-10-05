from typing import Any, Optional
import datetime
import uuid

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Date,
    DateTime,
    Double,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Articles(Base):
    __tablename__ = "articles"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="articles_pkey"),
        UniqueConstraint("pmcid", name="articles_pmcid_key"),
        Index("idx_articles_pmcid", "pmcid"),
        Index("idx_articles_publication_date", "publication_date"),
        Index("idx_articles_title_search", "title_search"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pmcid: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    journal: Mapped[Optional[str]] = mapped_column(String(255))
    doi: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    title_search: Mapped[Optional[Any]] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english'::regconfig, COALESCE(title, ''::text))",
            persisted=True,
        ),
    )
    citations: Mapped[Optional[int]] = mapped_column(Integer)

    organism: Mapped[list["Organisms"]] = relationship(
        "Organisms", secondary="article_organisms", back_populates="article"
    )
    article_authors: Mapped[list["ArticleAuthors"]] = relationship(
        "ArticleAuthors", back_populates="article"
    )
    article_citations: Mapped[list["ArticleCitations"]] = relationship(
        "ArticleCitations",
        foreign_keys="[ArticleCitations.cited_article_id]",
        back_populates="cited_article",
    )
    article_citations_: Mapped[list["ArticleCitations"]] = relationship(
        "ArticleCitations",
        foreign_keys="[ArticleCitations.citing_article_id]",
        back_populates="citing_article",
    )
    article_experiments: Mapped[list["ArticleExperiments"]] = relationship(
        "ArticleExperiments", back_populates="article"
    )
    article_funding: Mapped[list["ArticleFunding"]] = relationship(
        "ArticleFunding", back_populates="article"
    )
    article_keywords: Mapped[list["ArticleKeywords"]] = relationship(
        "ArticleKeywords", back_populates="article"
    )
    article_relationships: Mapped[list["ArticleRelationships"]] = relationship(
        "ArticleRelationships",
        foreign_keys="[ArticleRelationships.article_id_1]",
        back_populates="articles",
    )
    article_relationships_: Mapped[list["ArticleRelationships"]] = relationship(
        "ArticleRelationships",
        foreign_keys="[ArticleRelationships.article_id_2]",
        back_populates="articles_",
    )
    article_sections: Mapped[list["ArticleSections"]] = relationship(
        "ArticleSections", back_populates="article"
    )
    article_topics: Mapped[list["ArticleTopics"]] = relationship(
        "ArticleTopics", back_populates="article"
    )


class Authors(Base):
    __tablename__ = "authors"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="authors_pkey"),
        UniqueConstraint("normalized_name", name="authors_normalized_name_key"),
        Index("idx_authors_name_trgm", "full_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    article_authors: Mapped[list["ArticleAuthors"]] = relationship(
        "ArticleAuthors", back_populates="author"
    )


class FundingSources(Base):
    __tablename__ = "funding_sources"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="funding_sources_pkey"),
        UniqueConstraint("name", name="funding_sources_name_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    abbreviation: Mapped[Optional[str]] = mapped_column(String(50))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    source_type: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    article_funding: Mapped[list["ArticleFunding"]] = relationship(
        "ArticleFunding", back_populates="funding_source"
    )


class Keywords(Base):
    __tablename__ = "keywords"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="keywords_pkey"),
        UniqueConstraint("keyword", name="keywords_keyword_key"),
        Index("idx_keywords_category", "category"),
        Index("idx_keywords_keyword_trgm", "keyword"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    article_keywords: Mapped[list["ArticleKeywords"]] = relationship(
        "ArticleKeywords", back_populates="keyword"
    )


class NasaExperiments(Base):
    __tablename__ = "nasa_experiments"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="nasa_experiments_pkey"),
        UniqueConstraint(
            "experiment_name", name="nasa_experiments_experiment_name_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mission: Mapped[Optional[str]] = mapped_column(Text)
    experiment_type: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    end_date: Mapped[Optional[datetime.date]] = mapped_column(Date)

    article_experiments: Mapped[list["ArticleExperiments"]] = relationship(
        "ArticleExperiments", back_populates="experiment"
    )


class Organisms(Base):
    __tablename__ = "organisms"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="organisms_pkey"),
        UniqueConstraint("scientific_name", name="organisms_scientific_name_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False)
    common_name: Mapped[Optional[str]] = mapped_column(String(255))
    organism_type: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    article: Mapped[list["Articles"]] = relationship(
        "Articles", secondary="article_organisms", back_populates="organism"
    )


class Topics(Base):
    __tablename__ = "topics"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="topics_pkey"),
        UniqueConstraint("name", name="topics_name_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )

    article_topics: Mapped[list["ArticleTopics"]] = relationship(
        "ArticleTopics", back_populates="topic"
    )


class Users(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_pkey"),
        UniqueConstraint("email", name="users_email_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[Optional[str]] = mapped_column(String(100))

    messages: Mapped[list["Messages"]] = relationship("Messages", back_populates="user")


t_v_article_sections_summary = Table(
    "v_article_sections_summary",
    Base.metadata,
    Column("pmcid", String(50)),
    Column("title", Text),
    Column("section_count", BigInteger),
    Column("total_words", BigInteger),
    Column("available_sections", ARRAY(Text())),
)


t_v_articles_with_authors = Table(
    "v_articles_with_authors",
    Base.metadata,
    Column("id", Integer),
    Column("pmcid", String(50)),
    Column("title", Text),
    Column("publication_date", Date),
    Column("journal", String(255)),
    Column("authors", Text),
)


t_v_research_topics = Table(
    "v_research_topics",
    Base.metadata,
    Column("keyword", String(255)),
    Column("category", Text),
    Column("article_count", BigInteger),
    Column("avg_relevance", Double(53)),
)


class ArticleAuthors(Base):
    __tablename__ = "article_authors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_authors_article_id_fkey",
        ),
        ForeignKeyConstraint(
            ["author_id"],
            ["authors.id"],
            ondelete="CASCADE",
            name="article_authors_author_id_fkey",
        ),
        PrimaryKeyConstraint("article_id", "author_id", name="article_authors_pkey"),
    )

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_position: Mapped[Optional[int]] = mapped_column(Integer)

    article: Mapped["Articles"] = relationship(
        "Articles", back_populates="article_authors"
    )
    author: Mapped["Authors"] = relationship(
        "Authors", back_populates="article_authors"
    )


class ArticleCitations(Base):
    __tablename__ = "article_citations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["cited_article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_citations_cited_article_id_fkey",
        ),
        ForeignKeyConstraint(
            ["citing_article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_citations_citing_article_id_fkey",
        ),
        PrimaryKeyConstraint(
            "citing_article_id", "cited_article_id", name="article_citations_pkey"
        ),
    )

    citing_article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cited_article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    citation_context: Mapped[Optional[str]] = mapped_column(Text)

    cited_article: Mapped["Articles"] = relationship(
        "Articles", foreign_keys=[cited_article_id], back_populates="article_citations"
    )
    citing_article: Mapped["Articles"] = relationship(
        "Articles",
        foreign_keys=[citing_article_id],
        back_populates="article_citations_",
    )


class ArticleExperiments(Base):
    __tablename__ = "article_experiments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_experiments_article_id_fkey",
        ),
        ForeignKeyConstraint(
            ["experiment_id"],
            ["nasa_experiments.id"],
            ondelete="CASCADE",
            name="article_experiments_experiment_id_fkey",
        ),
        PrimaryKeyConstraint(
            "article_id", "experiment_id", name="article_experiments_pkey"
        ),
    )

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_primary_study: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )

    article: Mapped["Articles"] = relationship(
        "Articles", back_populates="article_experiments"
    )
    experiment: Mapped["NasaExperiments"] = relationship(
        "NasaExperiments", back_populates="article_experiments"
    )


class ArticleFunding(Base):
    __tablename__ = "article_funding"
    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_funding_article_id_fkey",
        ),
        ForeignKeyConstraint(
            ["funding_source_id"],
            ["funding_sources.id"],
            ondelete="CASCADE",
            name="article_funding_funding_source_id_fkey",
        ),
        PrimaryKeyConstraint(
            "article_id", "funding_source_id", name="article_funding_pkey"
        ),
        Index("idx_article_funding_article", "article_id"),
        Index("idx_article_funding_source", "funding_source_id"),
    )

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    funding_source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grant_number: Mapped[Optional[str]] = mapped_column(String(100))

    article: Mapped["Articles"] = relationship(
        "Articles", back_populates="article_funding"
    )
    funding_source: Mapped["FundingSources"] = relationship(
        "FundingSources", back_populates="article_funding"
    )


class ArticleKeywords(Base):
    __tablename__ = "article_keywords"
    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_keywords_article_id_fkey",
        ),
        ForeignKeyConstraint(
            ["keyword_id"],
            ["keywords.id"],
            ondelete="CASCADE",
            name="article_keywords_keyword_id_fkey",
        ),
        PrimaryKeyConstraint("article_id", "keyword_id", name="article_keywords_pkey"),
        Index("idx_article_keywords_article", "article_id"),
        Index("idx_article_keywords_keyword", "keyword_id"),
    )

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(
        Double(53), server_default=text("1.0")
    )
    extraction_method: Mapped[Optional[str]] = mapped_column(Text)

    article: Mapped["Articles"] = relationship(
        "Articles", back_populates="article_keywords"
    )
    keyword: Mapped["Keywords"] = relationship(
        "Keywords", back_populates="article_keywords"
    )


class ArticleMetadata(Articles):
    __tablename__ = "article_metadata"
    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_metadata_article_id_fkey",
        ),
        PrimaryKeyConstraint("article_id", name="article_metadata_pkey"),
        Index("idx_article_metadata_custom", "custom_fields"),
        Index("idx_article_metadata_sections", "all_sections"),
    )

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    all_sections: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_html_path: Mapped[Optional[str]] = mapped_column(Text)
    processing_notes: Mapped[Optional[dict]] = mapped_column(JSONB)
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSONB)


t_article_organisms = Table(
    "article_organisms",
    Base.metadata,
    Column("article_id", Integer, primary_key=True),
    Column("organism_id", Integer, primary_key=True),
    ForeignKeyConstraint(
        ["article_id"],
        ["articles.id"],
        ondelete="CASCADE",
        name="article_organisms_article_id_fkey",
    ),
    ForeignKeyConstraint(
        ["organism_id"],
        ["organisms.id"],
        ondelete="CASCADE",
        name="article_organisms_organism_id_fkey",
    ),
    PrimaryKeyConstraint("article_id", "organism_id", name="article_organisms_pkey"),
)


class ArticleRelationships(Base):
    __tablename__ = "article_relationships"
    __table_args__ = (
        CheckConstraint(
            "article_id_1 < article_id_2", name="article_relationships_check"
        ),
        ForeignKeyConstraint(
            ["article_id_1"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_relationships_article_id_1_fkey",
        ),
        ForeignKeyConstraint(
            ["article_id_2"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_relationships_article_id_2_fkey",
        ),
        PrimaryKeyConstraint(
            "article_id_1", "article_id_2", name="article_relationships_pkey"
        ),
    )

    article_id_1: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id_2: Mapped[int] = mapped_column(Integer, primary_key=True)
    relationship_type: Mapped[Optional[str]] = mapped_column(Text)
    similarity_score: Mapped[Optional[float]] = mapped_column(Double(53))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    articles: Mapped["Articles"] = relationship(
        "Articles", foreign_keys=[article_id_1], back_populates="article_relationships"
    )
    articles_: Mapped["Articles"] = relationship(
        "Articles", foreign_keys=[article_id_2], back_populates="article_relationships_"
    )


class ArticleSections(Base):
    __tablename__ = "article_sections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_sections_article_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="article_sections_pkey"),
        Index("idx_article_sections_article_id", "article_id"),
        Index("idx_article_sections_type", "section_type"),
        Index("idx_sections_content_search", "content_search"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    article_id: Mapped[Optional[int]] = mapped_column(Integer)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    section_order: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    content_search: Mapped[Optional[Any]] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english'::regconfig, COALESCE(content, ''::text))",
            persisted=True,
        ),
    )

    article: Mapped[Optional["Articles"]] = relationship(
        "Articles", back_populates="article_sections"
    )


class ArticleTopics(Base):
    __tablename__ = "article_topics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
            name="article_topics_article_id_fkey",
        ),
        ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="CASCADE",
            name="article_topics_topic_id_fkey",
        ),
        PrimaryKeyConstraint("article_id", "topic_id", name="article_topics_pkey"),
        Index("idx_article_topics_article", "article_id"),
        Index("idx_article_topics_topic", "topic_id"),
    )

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(
        Double(53), server_default=text("1.0")
    )
    is_primary: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text("false")
    )

    article: Mapped["Articles"] = relationship(
        "Articles", back_populates="article_topics"
    )
    topic: Mapped["Topics"] = relationship("Topics", back_populates="article_topics")


class Messages(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "direction::text = ANY (ARRAY['inbound'::character varying, 'outbound'::character varying]::text[])",
            name="messages_direction_check",
        ),
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="messages_user_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="messages_pkey"),
        Index("idx_messages_user_type", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, server_default=text("now()")
    )

    user: Mapped["Users"] = relationship("Users", back_populates="messages")
