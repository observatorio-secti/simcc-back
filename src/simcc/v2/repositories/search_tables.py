"""Definições de tabelas e visões materializadas para busca textual v2."""

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
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
