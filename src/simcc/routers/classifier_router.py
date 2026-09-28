"""Classifier endpoints backed by database and pipeline services."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from simcc.ai.dependencies import get_llm_provider
from simcc.core.dependencies import get_settings
from simcc.core.settings import Settings
from simcc.repositories import classifier_document_repository
from simcc.services import (
    classifier_pipeline_service,
    classifier_taxonomy_service,
    classifier_trace_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/classifier', tags=['classifier'])


def _slug(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_')


@router.get('/taxonomies')
def list_taxonomies(settings: Settings = Depends(get_settings)):
    return classifier_taxonomy_service.list_taxonomies(settings).model_dump()


@router.get('/taxonomies/{name}/graph')
def get_taxonomy_graph(
    name: str,
    origins: list[str] | None = Query(None),
    min_layer: int | None = Query(None, ge=0),
    max_layer: int | None = Query(None, ge=0),
    settings: Settings = Depends(get_settings),
):
    try:
        res = classifier_taxonomy_service.get_taxonomy_graph(
            settings=settings,
            taxonomy_name=name,
            origins=origins,
            min_layer=min_layer,
            max_layer=max_layer,
        )
        return res.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get('/pipeline/documents/summary')
def documents_summary(
    min_year: int = Query(2017, ge=2000),
):
    res = classifier_pipeline_service.get_pipeline_documents_summary(min_year=min_year)
    return res.model_dump()


@router.post('/pipeline/run/{taxonomy_name}')
async def run_pipeline(
    taxonomy_name: str,
    min_year: int = Query(2017, ge=2000),
    settings: Settings = Depends(get_settings),
):
    async def event_generator() -> AsyncIterator[str]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _execute_pipeline():
            try:
                context = classifier_pipeline_service.prepare_pipeline(settings, taxonomy_name)
                for step, msg in classifier_pipeline_service.run_pipeline(settings, context, min_year=min_year):
                    payload = {
                        "step": step,
                        "total_steps": classifier_pipeline_service.TOTAL_STEPS,
                        "message": msg,
                        "text": msg,
                        "kind": "success" if msg.startswith("✅") else "info",
                    }
                    queue.put_nowait(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception as exc:
                logger.exception("Erro durante o pipeline")
                err_payload = json.dumps(
                    {"error": str(exc), "text": f"Erro: {str(exc)}", "kind": "error"},
                    ensure_ascii=False,
                ) + "\n"
                queue.put_nowait(err_payload)
            finally:
                queue.put_nowait(None)  # sentinel

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, _execute_pipeline)

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        await future  # propagate any executor exception

    return StreamingResponse(
        event_generator(),
        media_type='application/x-ndjson',
    )


@router.post('/taxonomies/generate')
async def generate_taxonomy(
    prompt: dict,
    llm=Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
):
    try:
        user_prompt = prompt.get('prompt', '')

        # Buscar amostragem de abstracts do banco de dados
        try:
            df = classifier_document_repository.fetch_documents(min_year=2015)
            abstracts = df["abstract"].sample(n=min(50, len(df)), random_state=42).tolist() if not df.empty else []
        except Exception as err:
            logger.warning("Erro ao buscar abstracts para amostragem: %s", err)
            abstracts = []

        if not abstracts:
            abstracts = ["Sem abstracts disponíveis no momento."]

        abstracts_text = "\n\n".join(abstracts[:20])
        json_template = (
            "{\n"
            '  "name": "nome_da_taxonomia",\n'
            '  "domain_description": "descrição do domínio baseada nos dados",\n'
            '  "area_examples": ["área1", "área2", "área3"],\n'
            '  "taxonomy_context": "contexto baseado nos abstracts",\n'
            '  "origin_label": "Generated",\n'
            '  "node_color": "#559FB8",\n'
            '  "area_filter_layer": 1,\n'
            '  "areas": [{"key": "area1", "title": "Área 1", "description": "Descrição"}]\n'
            "}"
        )
        enriched_prompt = (
            f"Baseado nos seguintes {len(abstracts)} abstracts de artigos científicos brasileiros, gere uma taxonomia hierárquica:\n\n"
            f"PROMPT DO USUÁRIO: {user_prompt}\n\n"
            f"ABSTRACTS SAMPLE:\n{abstracts_text[:10000]}\n\n"
            f"Responda APENAS em formato JSON válido com esta estrutura:\n{json_template}\n\n"
            "As áreas devem ser derivadas dos temas presentes nos abstracts acima."
        )

        generated = await llm.generate(enriched_prompt)
        try:
            m = re.search(r'\{[\s\S]*\}', generated)
            config = json.loads(m.group(0)) if m else None
        except (json.JSONDecodeError, AttributeError):
            config = None

        if not config:
            config = {
                'name': 'Taxonomia Gerada',
                'domain_description': user_prompt,
                'area_examples': [],
                'taxonomy_context': user_prompt,
                'origin_label': 'Generated',
                'node_color': '#559FB8',
                'area_filter_layer': 1,
                'areas': [],
            }
        config.setdefault('areas', [])
        config.setdefault('name', 'Taxonomia Gerada')

        taxonomies_dir = settings.taxonomies_dir
        taxonomies_dir.mkdir(parents=True, exist_ok=True)

        slug = _slug(config.get('name', 'taxonomia_generada'))
        taxonomy_path = taxonomies_dir / f'{slug}_taxonomy.json'
        config_path = taxonomies_dir / f'{slug}_config.json'

        children = []
        for area in config.get('areas', []):
            area_title = area.get('title', area.get('key', str(area))) if isinstance(area, dict) else str(area)
            children.append({
                'name': area_title,
                'children': []
            })
        taxonomy_path.write_text(json.dumps({'name': config['name'], 'children': children}, ensure_ascii=False, indent=2), encoding='utf-8')
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')

        return {'generated': config}
    except Exception as e:
        logger.exception("Erro ao gerar taxonomia")
        raise HTTPException(500, f'Erro ao gerar taxonomia: {str(e)}')


@router.post('/taxonomies/structure/save')
async def save_taxonomy(body: dict, settings: Settings = Depends(get_settings)):
    config = body.get('config', {})
    taxonomy_name = config.get('name', 'unnamed')
    slug = _slug(taxonomy_name)
    taxonomies_dir = settings.taxonomies_dir
    taxonomies_dir.mkdir(parents=True, exist_ok=True)
    taxonomy_path = taxonomies_dir / f'{slug}_taxonomy.json'
    config_path = taxonomies_dir / f'{slug}_config.json'
    if not taxonomy_path.exists():
        children = [{'name': a.get('title', str(a)), 'children': []} for a in config.get('areas', [])]
        taxonomy_path.write_text(json.dumps({'name': taxonomy_name, 'children': children}, ensure_ascii=False, indent=2), encoding='utf-8')
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    return {
        'taxonomy_name': taxonomy_name,
        'config_path': str(config_path),
        'taxonomy_path': str(taxonomy_path),
        'message': 'Taxonomia salva com sucesso',
    }


@router.get('/trace/areas')
def get_areas(taxonomy_name: str, settings: Settings = Depends(get_settings)):
    try:
        return classifier_trace_service.get_area_trace(settings, taxonomy_name).model_dump()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get('/trace/topics')
def get_topics(taxonomy_name: str, settings: Settings = Depends(get_settings)):
    try:
        return classifier_trace_service.get_topic_trace(settings, taxonomy_name).model_dump()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get('/trace/subtopics')
def get_subtopics(taxonomy_name: str, settings: Settings = Depends(get_settings)):
    try:
        return classifier_trace_service.get_subtopic_trace(settings, taxonomy_name).model_dump()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get('/trace/researchers')
def get_researchers(
    taxonomy_name: str,
    min_year: int | None = Query(None, ge=2000),
    max_year: int | None = Query(None, ge=2000),
    settings: Settings = Depends(get_settings),
):
    try:
        return classifier_trace_service.get_researcher_trace(
            settings, taxonomy_name, min_year, max_year
        ).model_dump()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get('/trace/articles')
def get_articles(
    taxonomy_name: str,
    min_year: int | None = Query(None, ge=2000),
    max_year: int | None = Query(None, ge=2000),
    settings: Settings = Depends(get_settings),
):
    try:
        return classifier_trace_service.get_article_trace(
            settings, taxonomy_name, min_year, max_year
        ).model_dump()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
