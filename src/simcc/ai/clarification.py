from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.ai.query_planner import QueryPlan
from simcc.ai.schemas.clarification import (
    ClarificationOption,
    ClarificationPayload,
    ClarificationResponse,
    ClarificationType,
)
from simcc.core.cache import CacheService
from simcc.services.researcher_matcher import ResearcherMatcher


class ClarificationManager:
    """
    Orquestrador extensível de clarificações conversacionais (Human-in-the-Loop).
    Gerencia o ciclo de vida de dúvidas, auto-resolução por score e persistência
    de estado de sessão no Redis.
    """

    def __init__(
        self,
        matcher: Optional[ResearcherMatcher] = None,
        cache: Optional[CacheService] = None,
    ):
        self.matcher = matcher or ResearcherMatcher()
        self.cache = cache

    async def evaluate_researcher_clarification(
        self,
        session: AsyncSession,
        plan: QueryPlan,
        session_id: Optional[str],
        original_query: str,
    ) -> Optional[ClarificationPayload]:
        """
        Avalia se a consulta requer desambiguação de pesquisador.
        Se houver alta confiança e certeza única, auto-resolve aplicando o ID.
        Se houver ambiguidade ou dúvida, monta o ClarificationPayload e salva a sessão.
        """
        # Se já foi resolvido/especificado diretamente, não requer clarificação
        if plan.filters.researcher_ids:
            return None

        raw_name = plan.filters.researcher_name
        if not raw_name or not raw_name.strip():
            return None

        # Continuidade conversacional: verifica se há um pesquisador ativo na sessão
        if self.cache and session_id:
            active_key = self.cache.build_key(
                'ai', 'session_active_researcher', session_id
            )
            active_data = await self.cache.get(active_key)
            if (
                isinstance(active_data, dict)
                and active_data.get('id')
                and active_data.get('name')
            ):
                active_name = active_data['name']
                active_tokens = set(
                    ResearcherMatcher.normalize_tokens(active_name)
                )
                raw_tokens = set(
                    ResearcherMatcher.normalize_tokens(raw_name)
                )
                if raw_tokens and raw_tokens.issubset(active_tokens):
                    # O usuário citou parte do nome já estabelecido na conversa
                    plan.filters.researcher_name = active_name
                    plan.filters.researcher_ids = [active_data['id']]
                    return None

        target_inst = (
            plan.filters.institutions[0]
            if plan.filters.institutions and len(plan.filters.institutions) == 1
            else None
        )

        candidates = await self.matcher.find_candidates(
            session=session,
            raw_name=raw_name,
            target_institution=target_inst,
            limit=4,
        )

        if not candidates:
            return None

        # Cenário 1: Apenas 1 candidato
        if len(candidates) == 1:
            if candidates[0].score >= 0.70:
                # Auto-resolução com confiança
                plan.filters.researcher_name = candidates[0].name
                plan.filters.researcher_ids = [candidates[0].id]
                if self.cache and session_id:
                    active_key = self.cache.build_key(
                        'ai', 'session_active_researcher', session_id
                    )
                    await self.cache.set(
                        active_key,
                        {'id': candidates[0].id, 'name': candidates[0].name},
                        ttl=1800,
                    )
                return None
            else:
                # Score baixo (erro de digitação severo com dúvida) -> pede confirmação
                options = [
                    ClarificationOption(
                        id=candidates[0].id,
                        label=candidates[0].name,
                        description=candidates[0].institution,
                        metadata={'score': candidates[0].score},
                    )
                ]
                return await self._create_and_cache_payload(
                    session_id=session_id,
                    plan=plan,
                    raw_name=raw_name,
                    original_query=original_query,
                    options=options,
                    question=(
                        f"Você gostaria de consultar dados de "
                        f"'{candidates[0].name}' ({candidates[0].institution})?"
                    ),
                )

        # Cenário 2: Múltiplos candidatos encontrados
        # Se o primeiro for match perfeito/quase absoluto e o segundo for muito distante
        if (
            candidates[0].score >= 0.95
            and (candidates[0].score - candidates[1].score) >= 0.25
        ):
            plan.filters.researcher_name = candidates[0].name
            plan.filters.researcher_ids = [candidates[0].id]
            if self.cache and session_id:
                active_key = self.cache.build_key(
                    'ai', 'session_active_researcher', session_id
                )
                await self.cache.set(
                    active_key,
                    {'id': candidates[0].id, 'name': candidates[0].name},
                    ttl=1800,
                )
            return None

        # Ambiguidade real: 2 a 4 pesquisadores plausíveis
        options = [
            ClarificationOption(
                id=c.id,
                label=c.name,
                description=c.institution,
                metadata={'score': c.score},
            )
            for c in candidates
        ]

        question = (
            f"Encontrei mais de um pesquisador compatível com '{raw_name}'. "
            f'De quem você gostaria de consultar as informações?'
        )

        return await self._create_and_cache_payload(
            session_id=session_id,
            plan=plan,
            raw_name=raw_name,
            original_query=original_query,
            options=options,
            question=question,
        )

    async def _create_and_cache_payload(
        self,
        session_id: Optional[str],
        plan: QueryPlan,
        raw_name: str,
        original_query: str,
        options: list[ClarificationOption],
        question: str,
    ) -> ClarificationPayload:
        payload = ClarificationPayload(
            type=ClarificationType.RESEARCHER_DISAMBIGUATION,
            question=question,
            field_to_bind='researcher_id',
            options=options,
            original_query=original_query,
            context={'plan': plan.model_dump(), 'raw_name': raw_name},
        )

        if self.cache and session_id:
            key = self.cache.build_key(
                'ai', 'clarification:session', session_id
            )
            await self.cache.set(key, payload.model_dump(), ttl=900)

        return payload

    async def resolve_pending_clarification(
        self,
        session_id: str,
        clarification_response: ClarificationResponse,
    ) -> Optional[QueryPlan]:
        """
        Recupera o plano suspenso no Redis e vincula a resposta escolhida pelo usuário.
        """
        if not self.cache or not session_id:
            return None

        key = self.cache.build_key('ai', 'clarification:session', session_id)
        saved = await self.cache.get(key)
        if not saved:
            return None

        await self.cache.delete(key)

        plan_dict = saved.get('context', {}).get('plan')
        if not plan_dict:
            return None

        plan = QueryPlan(**plan_dict)
        if clarification_response.field == 'researcher_id':
            plan.filters.researcher_ids = [clarification_response.value]
            for opt in saved.get('options', []):
                if opt.get('id') == clarification_response.value:
                    plan.filters.researcher_name = opt.get('label')
                    break

            if self.cache and session_id and plan.filters.researcher_name:
                active_key = self.cache.build_key(
                    'ai', 'session_active_researcher', session_id
                )
                await self.cache.set(
                    active_key,
                    {
                        'id': clarification_response.value,
                        'name': plan.filters.researcher_name,
                    },
                    ttl=1800,
                )

        return plan
