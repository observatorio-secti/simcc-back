"""Definições de tabelas e visões materializadas para busca textual v2."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

search_metadata = MetaData()

mv_researcher_search = Table(
    'mv_researcher_search',
    search_metadata,
    Column('researcher_id', PG_UUID(as_uuid=True), primary_key=True),
    Column('name', String, nullable=False),
    Column('graduation', String, nullable=True),
    Column('classification', String, nullable=True),
    Column('lattes_update', DateTime, nullable=True),
    Column('articles', Integer, nullable=False),
    Column('book_chapters', Integer, nullable=False),
    Column('books', Integer, nullable=False),
    Column('patents', Integer, nullable=False),
    Column('software', Integer, nullable=False),
    Column('brands', Integer, nullable=False),
    Column('institution_ids', ARRAY(PG_UUID(as_uuid=True)), nullable=False),
    Column('city_ids', ARRAY(PG_UUID(as_uuid=True)), nullable=False),
    Column('identity_territories', ARRAY(String), nullable=False),
    Column(
        'graduate_program_ids', ARRAY(PG_UUID(as_uuid=True)), nullable=False
    ),
    Column('production_years', ARRAY(Integer), nullable=False),
    Column('profile_vector', TSVECTOR, nullable=True),
)

mv_search_documents = Table(
    'mv_search_documents',
    search_metadata,
    Column('researcher_id', PG_UUID(as_uuid=True), nullable=False),
    Column('source_id', PG_UUID(as_uuid=True), primary_key=True),
    Column('source_type', String, primary_key=True),
    Column('title', String, nullable=True),
    Column('year_', Integer, nullable=True),
    Column('search_vector', TSVECTOR, nullable=True),
)

mv_canonical_articles = Table(
    'mv_canonical_articles',
    search_metadata,
    Column('canonical_id', PG_UUID(as_uuid=True), primary_key=True),
    Column('production_ids', ARRAY(PG_UUID(as_uuid=True)), nullable=False),
    Column('researcher_ids', ARRAY(PG_UUID(as_uuid=True)), nullable=False),
    Column('institution_ids', ARRAY(PG_UUID(as_uuid=True)), nullable=True),
    Column(
        'graduate_program_ids', ARRAY(PG_UUID(as_uuid=True)), nullable=True
    ),
    Column('platform_authors', JSONB, nullable=True),
    Column('title', String, nullable=False),
    Column('year', Integer, nullable=True),
    Column('doi', String, nullable=True),
    Column('qualis', String, nullable=True),
    Column('jcr', String, nullable=True),
    Column('magazine_name', String, nullable=True),
    Column('issn', String, nullable=True),
    Column('abstract', Text, nullable=True),
    Column('citations_count', Integer, nullable=False, default=0),
    Column('landing_page_url', Text, nullable=True),
    Column('pdf_url', Text, nullable=True),
    Column('keywords', Text, nullable=True),
    Column('all_authors_raw', Text, nullable=True),
    Column('language', String, nullable=True),
    Column('has_abstract', Boolean, nullable=False),
    Column('has_open_access_pdf', Boolean, nullable=False),
    Column('search_vector', TSVECTOR, nullable=True),
)
