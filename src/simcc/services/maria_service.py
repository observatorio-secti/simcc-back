import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from simcc.ai.chat_history import SIMCCChatMessageHistory
from simcc.ai.clarification import ClarificationManager
from simcc.ai.prompts.maria_prompts import (
    MARIA_EMPTY_FALLBACK_MESSAGE,
    MARIA_PROMPT_TEMPLATE,
    SUMMARY_SEARCH_PROMPT,
    build_synthesis_prompt,
)
from simcc.ai.providers.base import EmbeddingsProvider, LLMProvider
from simcc.ai.schemas.clarification import (
    ClarificationResponse,
)
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
from simcc.services.ai_metrics_service import AIMetricsService

logger = logging.getLogger(__name__)


class MariaService:
    def __init__(
        self,
        llm: LLMProvider,
        embeddings: EmbeddingsProvider,
        cache: Optional[CacheService] = None,
        tracer: Optional[AITracer] = None,
        clarification_manager: Optional[ClarificationManager] = None,
        metrics_service: Optional[AIMetricsService] = None,
    ):
        self.llm = llm
        self.embeddings = embeddings
        self.cache = cache
        self.tracer = tracer
        self.clarification_manager = clarification_manager
        self.metrics_service = metrics_service or AIMetricsService()

    async def _enrich_metrics_and_context(
        self,
        session,
        plan,
        researchers: List[Dict[str, Any]],
        productions: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self.metrics_service or not session:
            return None

        try:
            all_rids = []
            for r in researchers:
                if r.get('id'):
                    all_rids.append(r['id'])
            for p in productions:
                r_info = p.get('researcher')
                if r_info and r_info.get('id'):
                    all_rids.append(r_info['id'])

            if all_rids:
                career_metrics = (
                    await self.metrics_service.get_researchers_career_metrics(
                        session=session,
                        researcher_ids=all_rids,
                    )
                )
                for r in researchers:
                    rid = str(r.get('id'))
                    if rid in career_metrics:
                        r['metrics'] = career_metrics[rid]

                for p in productions:
                    r_info = p.get('researcher')
                    if r_info and str(r_info.get('id')) in career_metrics:
                        r_info['metrics'] = career_metrics[
                            str(r_info.get('id'))
                        ]

            sample_count = (
                len(productions) if productions else len(researchers)
            )
            return await self.metrics_service.get_global_search_context(
                session=session,
                plan=plan,
                sample_count=sample_count,
            )
        except Exception as ex:
            logger.warning(f'Erro ao enriquecer métricas na MarIA: {ex}')
            return None

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

    def get_chat_history(self, session_id: str) -> SIMCCChatMessageHistory:
        return SIMCCChatMessageHistory(
            session_id=session_id,
            cache_service=self.cache,
            max_messages=10,
        )

    @staticmethod
    def _is_production_in_temporal_window(
        prod: dict, year_from: Optional[int], year_to: Optional[int]
    ) -> bool:
        raw_year = prod.get('year')
        if not raw_year:
            return False
        try:
            y = int(str(raw_year)[:4])
            if year_from is not None and y < year_from:
                return False
            if year_to is not None and y > year_to:
                return False
            return True
        except (ValueError, TypeError):
            return False

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
        self,
        session,
        query: str,
        planner,
        search_service,
        session_id: Optional[str] = None,
        clarification_response: Optional[ClarificationResponse] = None,
    ) -> ChatResponse:
        tracer = self.tracer or AITracer(query=query)
        cache_key = None

        history_handler = (
            self.get_chat_history(session_id) if session_id else None
        )
        chat_history: List[BaseMessage] = (
            await history_handler.aget_messages() if history_handler else []
        )

        plan = None
        if (
            clarification_response
            and self.clarification_manager
            and session_id
        ):
            plan = (
                await self.clarification_manager.resolve_pending_clarification(
                    session_id=session_id,
                    clarification_response=clarification_response,
                )
            )
            if plan and history_handler and plan.filters.researcher_name:
                await history_handler.aadd_messages([
                    HumanMessage(
                        content=f'[Selecionado]: {plan.filters.researcher_name}'
                    )
                ])

        if not plan:
            if not clarification_response and self.cache:
                canonical_hash = self.cache.hash_payload(
                    {'query': query.strip()}
                )
                cache_key = self.cache.build_key(
                    'ai', 'chat:batch', canonical_hash
                )
                cached_val = await self.cache.get(cache_key)
                if cached_val:
                    tracer.set_meta('cache_hit', True)
                    trace_summary = tracer.finish(status='success')
                    resp_data = dict(cached_val)
                    resp_data['telemetry'] = trace_summary
                    return ChatResponse(**resp_data)

        try:
            # 1. Planner
            if not plan:
                async with tracer.trace_stage('planner'):
                    try:
                        plan = await planner.plan(
                            query, chat_history=chat_history
                        )
                    except TypeError:
                        plan = await planner.plan(query)
                    tracer.set_meta('intent', plan.intent)

                # 1.5 Clarificação Conversacional (Human-in-the-Loop)
                if self.clarification_manager:
                    clarification = await self.clarification_manager.evaluate_researcher_clarification(
                        session=session,
                        plan=plan,
                        session_id=session_id,
                        original_query=query,
                    )
                    if clarification:
                        trace_summary = tracer.finish(status='success')
                        if history_handler:
                            await history_handler.aadd_messages([
                                HumanMessage(content=query),
                                AIMessage(content=clarification.question),
                            ])
                        return ChatResponse(
                            answer=clarification.question,
                            intent=plan.intent,
                            filters_extracted=plan.filters.model_dump(
                                exclude_none=True
                            ),
                            researchers=[],
                            productions=[],
                            sources=[],
                            telemetry=trace_summary,
                            clarification=clarification,
                        )

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
                    if (
                        plan.filters.year_from is not None
                        or plan.filters.year_to is not None
                    ):
                        productions = [
                            p
                            for p in productions
                            if self._is_production_in_temporal_window(
                                p,
                                plan.filters.year_from,
                                plan.filters.year_to,
                            )
                        ]

            global_metrics = await self._enrich_metrics_and_context(
                session=session,
                plan=plan,
                researchers=researchers,
                productions=productions,
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
                        global_metrics=global_metrics,
                        chat_history=chat_history,
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
                        global_metrics=global_metrics,
                        chat_history=chat_history,
                    )
                    answer = await self.llm.generate(synthesis_prompt)

            trace_summary = tracer.finish(status='success')
            sources = self._build_sources(researchers, productions)
            response = ChatResponse(
                answer=answer,
                intent=plan.intent,
                filters_extracted=filters_dict,
                researchers=researchers,
                productions=productions,
                sources=sources,
                telemetry=trace_summary,
                global_metrics=global_metrics,
            )

            # Grava no histórico conversacional da sessão
            if history_handler and answer:
                await history_handler.aadd_messages([
                    HumanMessage(content=query),
                    AIMessage(content=answer),
                ])

            # 4. Gravação em Cache
            if self.cache and cache_key:
                await self.cache.set(cache_key, response.model_dump())

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
        clarification_response: Optional[ClarificationResponse] = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        msg_id = message_id or f'msg_{uuid4().hex[:12]}'
        tracer = self.tracer or AITracer(request_id=msg_id, query=query)
        cache_key = None

        session_id = message_id
        history_handler = (
            self.get_chat_history(session_id) if session_id else None
        )
        chat_history: List[BaseMessage] = (
            await history_handler.aget_messages() if history_handler else []
        )

        plan = None
        if (
            clarification_response
            and self.clarification_manager
            and message_id
        ):
            plan = (
                await self.clarification_manager.resolve_pending_clarification(
                    session_id=message_id,
                    clarification_response=clarification_response,
                )
            )
            if plan and history_handler and plan.filters.researcher_name:
                await history_handler.aadd_messages([
                    HumanMessage(
                        content=f'[Selecionado]: {plan.filters.researcher_name}'
                    )
                ])

        if not plan:
            if not clarification_response and self.cache:
                canonical_hash = self.cache.hash_payload(
                    {'query': query.strip()}
                )
                cache_key = self.cache.build_key(
                    'ai', 'chat:stream', canonical_hash
                )
                cached_events = await self.cache.get(cache_key)
                if cached_events and isinstance(cached_events, list):
                    tracer.set_meta('cache_hit', True)
                    trace_summary = tracer.finish(status='success')
                    for ev in cached_events:
                        ev_dict = dict(ev)
                        ev_dict['message_id'] = msg_id
                        if ev_dict.get('type') == 'done':
                            ev_dict['data'] = {'telemetry': trace_summary}
                        yield ChatStreamEvent(**ev_dict)
                        if ev_dict.get('type') == 'delta':
                            await asyncio.sleep(0.015)
                    return

        accumulated_events: List[Dict[str, Any]] = []

        try:
            # 1. Planejamento
            if not plan:
                async with tracer.trace_stage('planner'):
                    try:
                        plan = await planner.plan(
                            query, chat_history=chat_history
                        )
                    except TypeError:
                        plan = await planner.plan(query)
                    tracer.set_meta('intent', plan.intent)

                # 1.5 Clarificação Conversacional (Human-in-the-Loop)
                if self.clarification_manager:
                    clarification = await self.clarification_manager.evaluate_researcher_clarification(
                        session=session,
                        plan=plan,
                        session_id=message_id,
                        original_query=query,
                    )
                    if clarification:
                        clarification_event = ChatStreamEvent(
                            type=ChatStreamEventType.CLARIFICATION,
                            message_id=msg_id,
                            content=clarification.question,
                            clarification=clarification,
                        )
                        accumulated_events.append(
                            clarification_event.model_dump()
                        )
                        if history_handler:
                            await history_handler.aadd_messages([
                                HumanMessage(content=query),
                                AIMessage(content=clarification.question),
                            ])
                        yield clarification_event

                        trace_summary = tracer.finish(status='success')
                        done_event = ChatStreamEvent(
                            type=ChatStreamEventType.DONE,
                            message_id=msg_id,
                            data={'telemetry': trace_summary},
                        )
                        accumulated_events.append(done_event.model_dump())
                        yield done_event
                        return

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
                    if (
                        plan.filters.year_from is not None
                        or plan.filters.year_to is not None
                    ):
                        productions = [
                            p
                            for p in productions
                            if self._is_production_in_temporal_window(
                                p,
                                plan.filters.year_from,
                                plan.filters.year_to,
                            )
                        ]

            global_metrics = await self._enrich_metrics_and_context(
                session=session,
                plan=plan,
                researchers=researchers,
                productions=productions,
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
                global_metrics=global_metrics,
            )

            meta_event = ChatStreamEvent(
                type=ChatStreamEventType.METADATA,
                message_id=msg_id,
                data=ui_metadata.model_dump(),
            )
            accumulated_events.append(meta_event.model_dump())
            yield meta_event

            # 4. Síntese / Emissão de Deltas
            full_answer = ''
            async with tracer.trace_stage('synthesis'):
                if plan.intent == 'general_question':
                    synthesis_prompt = build_synthesis_prompt(
                        query=query,
                        intent=plan.intent,
                        filters_dict=filters_dict,
                        researchers=[],
                        productions=[],
                        global_metrics=global_metrics,
                        chat_history=chat_history,
                    )
                    async for chunk in self.llm.generate_stream(
                        synthesis_prompt
                    ):
                        full_answer += chunk
                        delta_event = ChatStreamEvent(
                            type=ChatStreamEventType.DELTA,
                            message_id=msg_id,
                            content=chunk,
                        )
                        accumulated_events.append(delta_event.model_dump())
                        yield delta_event
                        await asyncio.sleep(0.015)
                elif total_found == 0:
                    full_answer = MARIA_EMPTY_FALLBACK_MESSAGE
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
                        global_metrics=global_metrics,
                        chat_history=chat_history,
                    )
                    async for chunk in self.llm.generate_stream(
                        synthesis_prompt
                    ):
                        full_answer += chunk
                        delta_event = ChatStreamEvent(
                            type=ChatStreamEventType.DELTA,
                            message_id=msg_id,
                            content=chunk,
                        )
                        accumulated_events.append(delta_event.model_dump())
                        yield delta_event
                        await asyncio.sleep(0.015)

            # Grava no histórico conversacional da sessão
            if history_handler and full_answer:
                await history_handler.aadd_messages([
                    HumanMessage(content=query),
                    AIMessage(content=full_answer),
                ])

            trace_summary = tracer.finish(status='success')
            done_event = ChatStreamEvent(
                type=ChatStreamEventType.DONE,
                message_id=msg_id,
                data={'telemetry': trace_summary},
            )
            accumulated_events.append(done_event.model_dump())
            yield done_event

            # 5. Gravação em Cache
            if self.cache and cache_key:
                await self.cache.set(cache_key, accumulated_events)

        except asyncio.CancelledError:
            tracer.finish(
                status='failed', error_message='Stream cancelled by client'
            )
            raise
        except Exception as exc:
            trace_summary = tracer.finish(
                status='failed', error_message=str(exc)
            )
            yield ChatStreamEvent(
                type=ChatStreamEventType.ERROR,
                message_id=msg_id,
                code='generation_failed',
                message=(
                    'Ocorreu um erro ao processar sua consulta com a MarIA.'
                ),
                data={'telemetry': trace_summary},
            )
