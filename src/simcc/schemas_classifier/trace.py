"""
schemas_classifier/trace.py — Schemas Pydantic para os endpoints de rastreabilidade.
"""
from __future__ import annotations

from pydantic import BaseModel


class AreaTraceItem(BaseModel):
    number: int
    area: str


class AreaTraceResponse(BaseModel):
    items: list[AreaTraceItem]
    total: int


class TopicTraceItem(BaseModel):
    topic: str
    area: str


class TopicTraceResponse(BaseModel):
    items: list[TopicTraceItem]
    total: int


class SubtopicTraceItem(BaseModel):
    subtopic: str
    topic: str
    area: str


class SubtopicTraceResponse(BaseModel):
    items: list[SubtopicTraceItem]
    total: int


class ResearcherTraceItem(BaseModel):
    researcher_name: str
    area_labels: str
    topic_label: str
    subtopic_label: str
    article_count: int


class ResearcherTraceResponse(BaseModel):
    items: list[ResearcherTraceItem]
    total: int


class ArticleTraceItem(BaseModel):
    title: str
    year: str | None
    researcher_name: str
    area_labels: str
    topic_label: str
    subtopic_label: str    
    periodical: str
    qualis: str
    jcr: str
    abstract: str


class ArticleTraceResponse(BaseModel):
    items: list[ArticleTraceItem]
    total: int
