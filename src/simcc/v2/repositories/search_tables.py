"""Definições de tabelas e visões materializadas para busca textual v2."""

from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

search_metadata = MetaData()

mv_researcher_search = Table(
    'mv_researcher_search',
    search_metadata,
    Column('researcher_id', PG_UUID(as_uuid=True), primary_key=True),
    Column('name', String, nullable=False),
    Column('institution_id', PG_UUID(as_uuid=True), nullable=True),
    Column('institution_name', String, nullable=True),
    Column('institution_acronym', String, nullable=True),
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
