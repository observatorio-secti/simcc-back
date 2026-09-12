import asyncio
from collections.abc import AsyncIterator
from typing import Any, Dict, List, Optional
from uuid import uuid4

from simcc.ai.prompts.maria_prompts import (
    MARIA_EMPTY_FALLBACK_MESSAGE,
    MARIA_PROMPT_TEMPLATE,
    SUMMARY_SEARCH_PROMPT,
    build_synthesis_prompt,
)
from simcc.ai.providers.base import EmbeddingsProvider, LLMProvider
from simcc.ai.schemas.maria import (
    ChatResponse,
    ChatStreamEvent,
    ChatStreamEventType,
    MariaResponse,
    SearchUIMetadata,
)
from simcc.ai.telemetry.tracer import AITracer
from simcc.core.cache import CacheService
from simcc.repositories import maria_repo, researcher_repo
from simcc.schemas import DefaultFilters
from simcc.services import production_service, researcher_service


class MariaService:
    def __init__(
        self,
        llm: LLMProvider,
        embeddings: EmbeddingsProvider,
        cache: Optional[CacheService] = None,
        tracer: Optional[AITracer] = None,
    ):
        self.llm = llm
        self.embeddings = embeddings
        self.cache = cache
        self.tracer = tracer

    @staticmethod
    def _get_compact_researcher_data(researcher: dict) -> dict:
        return {
            'name': researcher.get('name'),
            'university': researcher.get('university'),
            'area': researcher.get('area'),
            'abstract': (researcher.get('abstract') or '')[:500] + '...'
            if researcher.get('abstract')
            else None,
            'articles': researcher.get('articles'),
            'h_index': researcher.get('h_index'),
        }

    @staticmethod
    def _build_ui_filters(filters) -> dict:
        ui_f = {}
        if filters.institutions:
            ui_f['institutions'] = filters.institutions
        if filters.researcher_name:
            ui_f['researcher_name'] = filters.researcher_name
        if filters.city:
            ui_f['city'] = filters.city
        if filters.year_from or filters.year_to:
            if filters.year_from and filters.year_to:
                ui_f['period'] = f'{filters.year_from} - {filters.year_to}'
            elif filters.year_from:
                ui_f['period'] = f'A partir de {filters.year_from}'
            else:
                ui_f['period'] = f'Até {filters.year_to}'
        return ui_f

    @staticmethod
    def _build_sources(researchers: list, productions: list) -> List[str]:
        sources = []
        if researchers:
            sources.extend([
                f'{r["name"]} ({r.get("institution_acronym") or r.get("institution") or "BA"})'
                for r in researchers
            ])
        if productions:
            sources.extend([
                f'{p.get("title")} [{p.get("type")}] '
                f'({p.get("year") or "S/D"})'
                for p in productions
            ])
        return sources

    async def search_and_summarize(
        self, session, query: str, search_type: str
    ) -> MariaResponse:
        vector = await self.embeddings.get_embeddings(query)
        researcher_ids = await maria_repo.search_by_embeddings(
            session, vector, search_type
        )

        if not researcher_ids:
            return MariaResponse(query='', researchers=[])

        filters = DefaultFilters(researcher_ids=researcher_ids)
        researchers_data = await researcher_repo.search_researchers(
            session, filters
        )

        data_to_summarize = [
            self._get_compact_researcher_data(dict(r))
            for r in researchers_data[:5]
        ]
        prompt = MARIA_PROMPT_TEMPLATE.format(
            area=search_type, data_dict=str(data_to_summarize)
        )
        comment = await self.llm.generate(prompt)

        return MariaResponse(query=comment, researchers=researchers_data)

    async def generate_search_summary(
        self, session, filters: DefaultFilters
    ) -> str:
        search_type = filters.type.upper() if filters.type else 'ARTICLE'
        limit = 5 if search_type in {'NAME', 'AREA'} else 10
        filters.lenght = limit
        filters.page = 1

        data = []
        if search_type == 'ARTICLE':
            data = await production_service.list_bibliographic_production(
                session, filters
            )
        elif search_type == 'BOOK':
            data = await production_service.list_book(session, filters)
        elif search_type == 'BOOK_CHAPTER':
            data = await production_service.list_book_chapter(session, filters)
        elif search_type == 'ABSTRACT':
            filters.type = 'ABSTRACT'
            data = await production_service.list_bibliographic_production(
                session, filters
            )
        elif search_type in {'NAME', 'AREA'}:
            data = await researcher_service.search_researchers(
                session, filters
            )
        elif search_type == 'WORK_IN_EVENT':
            data = await production_service.list_researcher_production_events(
                session, filters
            )
        elif search_type == 'PATENT':
            data = await production_service.list_patent(session, filters)
        elif search_type == 'EVENT':
            data = await production_service.list_participation_event(
                session, filters
            )
        else:
            data = await production_service.list_bibliographic_production(
                session, filters
            )

        if not data:
            return 'Nenhum resultado relevante encontrado para gerar o resumo.'

        if search_type in {'NAME', 'AREA'}:
            data_to_summarize = [
                self._get_compact_researcher_data(dict(r))
                for r in data[:limit]
            ]
        else:
            data_to_summarize = [dict(r) for r in data[:limit]]

        prompt = SUMMARY_SEARCH_PROMPT.format(data_dict=str(data_to_summarize))
        return await self.llm.generate(prompt)

    async def chat_ask(
        self, session, query: str, planner, search_service
    ) -> ChatResponse:
        tracer = self.tracer or AITracer(query=query)
        cache_key = None

        if self.cache:
            canonical_hash = self.cache.hash_payload({'query': query.strip()})
            cache_key = self.cache.build_key(
                'ai', 'chat:batch', canonical_hash
            )
            cached_val = await self.cache.get(cache_key)
            if cached_val:
                tracer.set_meta('cache_hit', True)
                tracer.finish(status='success')
                return ChatResponse(**cached_val)

        try:
            # 1. Planner
            async with tracer.trace_stage('planner'):
                plan = await planner.plan(query)
                tracer.set_meta('intent', plan.intent)

            # 2. Busca Híbrida
            researchers = []
            productions = []
            filters_dict = plan.filters.model_dump(exclude_none=True)

            async with tracer.trace_stage('search'):
                if plan.intent in {
                    'researcher_search',
                    'researcher_profile',
                    'aggregation',
                }:
                    researchers = (
                        await search_service.search_researchers_hybrid(
                            session=session,
                            query=plan.semantic_query,
                            limit=10,
                            filters=filters_dict,
                        )
                    )
                elif plan.intent == 'production_search':
                    productions = (
                        await search_service.search_productions_hybrid(
                            session=session,
                            query=plan.semantic_query,
                            limit=10,
                            filters=filters_dict,
                        )
                    )

            total_found = len(researchers) + len(productions)
            tracer.set_meta('final_count', total_found)

            # 3. Síntese
            async with tracer.trace_stage('synthesis'):
                if plan.intent == 'general_question':
                    synthesis_prompt = build_synthesis_prompt(
                        query=query,
                        intent=plan.intent,
                        filters_dict=filters_dict,
                        researchers=[],
                        productions=[],
                    )
                    answer = await self.llm.generate(synthesis_prompt)
                elif total_found == 0:
                    answer = MARIA_EMPTY_FALLBACK_MESSAGE
                else:
                    synthesis_prompt = build_synthesis_prompt(
                        query=query,
                        intent=plan.intent,
                        filters_dict=filters_dict,
                        researchers=researchers,
                        productions=productions,
                    )
                    answer = await self.llm.generate(synthesis_prompt)

            sources = self._build_sources(researchers, productions)
            response = ChatResponse(
                answer=answer,
                intent=plan.intent,
                filters_extracted=filters_dict,
                researchers=researchers,
                productions=productions,
                sources=sources,
            )

            # 4. Gravação em Cache
            if self.cache and cache_key:
                await self.cache.set(cache_key, response.model_dump())

            tracer.finish(status='success')
            return response

        except Exception as exc:
            tracer.finish(status='failed', error_message=str(exc))
            raise

    async def chat_ask_stream(
        self,
        session,
        query: str,
        planner,
        search_service,
        message_id: Optional[str] = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        msg_id = message_id or f'msg_{uuid4().hex[:12]}'
        tracer = self.tracer or AITracer(request_id=msg_id, query=query)
        cache_key = None
        if self.cache:
            canonical_hash = self.cache.hash_payload({'query': query.strip()})
            cache_key = self.cache.build_key(
                'ai', 'chat:stream', canonical_hash
            )
            cached_events = await self.cache.get(cache_key)
            if cached_events and isinstance(cached_events, list):
                tracer.set_meta('cache_hit', True)
                tracer.finish(status='success')
                for ev in cached_events:
                    ev_dict = dict(ev)
                    ev_dict['message_id'] = msg_id
                    yield ChatStreamEvent(**ev_dict)
                return

        accumulated_events: List[Dict[str, Any]] = []

        try:
            # 1. Planejamento
            async with tracer.trace_stage('planner'):
                plan = await planner.plan(query)
                tracer.set_meta('intent', plan.intent)

            # 2. Busca Híbrida
            researchers = []
            productions = []
            filters_dict = plan.filters.model_dump(exclude_none=True)

            async with tracer.trace_stage('search'):
                if plan.intent in {
                    'researcher_search',
                    'researcher_profile',
                    'aggregation',
                }:
                    researchers = (
                        await search_service.search_researchers_hybrid(
                            session=session,
                            query=plan.semantic_query,
                            limit=10,
                            filters=filters_dict,
                        )
                    )
                elif plan.intent == 'production_search':
                    productions = (
                        await search_service.search_productions_hybrid(
                            session=session,
                            query=plan.semantic_query,
                            limit=10,
                            filters=filters_dict,
                        )
                    )

            total_found = len(researchers) + len(productions)
            tracer.set_meta('final_count', total_found)

            # 3. Metadados e Fontes
            sources = self._build_sources(researchers, productions)
            ui_filters = self._build_ui_filters(plan.filters)

            ui_metadata = SearchUIMetadata(
                intent=plan.intent,
                filters=ui_filters,
                researchers=researchers,
                productions=productions,
                sources=sources,
            )

            meta_event = ChatStreamEvent(
                type=ChatStreamEventType.METADATA,
                message_id=msg_id,
                data=ui_metadata.model_dump(),
            )
            accumulated_events.append(meta_event.model_dump())
            yield meta_event

            # 4. Síntese / Emissão de Deltas
            async with tracer.trace_stage('synthesis'):
                if plan.intent == 'general_question':
                    synthesis_prompt = build_synthesis_prompt(
                        query=query,
                        intent=plan.intent,
                        filters_dict=filters_dict,
                        researchers=[],
                        productions=[],
                    )
                    async for chunk in self.llm.generate_stream(
                        synthesis_prompt
                    ):
                        delta_event = ChatStreamEvent(
                            type=ChatStreamEventType.DELTA,
                            message_id=msg_id,
                            content=chunk,
                        )
                        accumulated_events.append(delta_event.model_dump())
                        yield delta_event
                elif total_found == 0:
                    delta_event = ChatStreamEvent(
                        type=ChatStreamEventType.DELTA,
                        message_id=msg_id,
                        content=MARIA_EMPTY_FALLBACK_MESSAGE,
                    )
                    accumulated_events.append(delta_event.model_dump())
                    yield delta_event
                else:
                    synthesis_prompt = build_synthesis_prompt(
                        query=query,
                        intent=plan.intent,
                        filters_dict=filters_dict,
                        researchers=researchers,
                        productions=productions,
                    )
                    async for chunk in self.llm.generate_stream(
                        synthesis_prompt
                    ):
                        delta_event = ChatStreamEvent(
                            type=ChatStreamEventType.DELTA,
                            message_id=msg_id,
                            content=chunk,
                        )
                        accumulated_events.append(delta_event.model_dump())
                        yield delta_event

            done_event = ChatStreamEvent(
                type=ChatStreamEventType.DONE, message_id=msg_id
            )
            accumulated_events.append(done_event.model_dump())
            yield done_event

            # 5. Gravação em Cache
            if self.cache and cache_key:
                await self.cache.set(cache_key, accumulated_events)

            tracer.finish(status='success')

        except asyncio.CancelledError:
            tracer.finish(
                status='failed', error_message='Stream cancelled by client'
            )
            raise
        except Exception as exc:
            tracer.finish(status='failed', error_message=str(exc))
            yield ChatStreamEvent(
                type=ChatStreamEventType.ERROR,
                message_id=msg_id,
                code='generation_failed',
                message=(
                    'Ocorreu um erro ao processar sua consulta com a MarIA.'
                ),
            )
