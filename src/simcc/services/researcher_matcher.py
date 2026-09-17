import re
import unicodedata
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.institution import Institution
from simcc.core.db.models.researcher import Researcher


class ResearcherCandidate(BaseModel):
    id: str = Field(description='UUID do pesquisador')
    name: str = Field(description='Nome completo do pesquisador')
    institution: Optional[str] = Field(
        None, description='Sigla ou nome da instituição'
    )
    score: float = Field(
        0.0, description='Grau de similaridade e relevância (0.0 a 1.0)'
    )
    lattes_id: Optional[str] = Field(None, description='ID Lattes')


class ResearcherMatcher:
    """
    Localizador inteligente de pesquisadores com tolerância a:
    - Omissão de sobrenomes intermediários (ex: 'Eduardo Jorge' -> 'Eduardo Manuel de Freitas Jorge')
    - Acentuação ausente ou incorreta (ex: 'Celia' -> 'Célia', 'Joao' -> 'João')
    - Erros ortográficos e de digitação (typos) via similaridade trigram (pg_trgm)
    """

    STOP_WORDS = {'de', 'da', 'do', 'dos', 'das', 'e'}

    @classmethod
    def strip_accents(cls, text: str) -> str:
        """Remove acentuação mantendo caracteres alfanuméricos."""
        normalized = unicodedata.normalize('NFD', text)
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    @classmethod
    def normalize_tokens(cls, text: str) -> List[str]:
        """Normaliza e extrai tokens significativos de um nome."""
        cleaned = cls.strip_accents(text.lower().strip())
        tokens = [
            t for t in re.split(r'[^a-z0-9]+', cleaned)
            if t and t not in cls.STOP_WORDS
        ]
        return tokens

    async def find_candidates(
        self,
        session: AsyncSession,
        raw_name: str,
        target_institution: Optional[str] = None,
        limit: int = 5,
    ) -> List[ResearcherCandidate]:
        if not raw_name or not raw_name.strip():
            return []

        tokens = self.normalize_tokens(raw_name)
        if not tokens:
            return []

        clean_search = ' '.join(tokens)
        unaccent_name = func.public.f_unaccent(func.lower(Researcher.name))

        # 1. Trigram similarity score via pg_trgm
        trgm_similarity = func.similarity(unaccent_name, clean_search)

        # 2. Token match (todos os tokens digitados devem existir no nome do pesquisador)
        token_filters = [
            unaccent_name.ilike(f'%{tok}%')
            for tok in tokens
        ]

        match_conditions = []
        if token_filters:
            match_conditions.append(and_(*token_filters))
        match_conditions.append(trgm_similarity >= 0.35)

        stmt = (
            select(
                Researcher.id,
                Researcher.name,
                Researcher.lattes_id,
                Institution.acronym,
                Institution.name.label('institution_name'),
                trgm_similarity.label('sim_score'),
            )
            .outerjoin(Institution, Institution.id == Researcher.institution_id)
            .filter(or_(*match_conditions))
        )

        if target_institution and target_institution.strip():
            inst_clean = target_institution.strip().lower()
            stmt = stmt.filter(
                or_(
                    func.lower(Institution.acronym).ilike(f'%{inst_clean}%'),
                    func.lower(Institution.name).ilike(f'%{inst_clean}%'),
                )
            )

        stmt = stmt.order_by(trgm_similarity.desc()).limit(limit)

        result = await session.execute(stmt)
        rows = result.all()

        candidates: List[ResearcherCandidate] = []
        for r_id, name, lattes_id, inst_acronym, inst_name, sim_score in rows:
            inst = inst_acronym or inst_name or 'Instituição não informada'
            base_sim = float(sim_score) if sim_score is not None else 0.0

            cand_tokens = self.normalize_tokens(name)
            all_tokens_present = all(tok in cand_tokens for tok in tokens)

            # Cálculo de score ponderado
            if clean_search == ' '.join(cand_tokens):
                final_score = 1.0
            elif all_tokens_present:
                # Todos os termos buscados existem no nome
                # Score elevado (ex: 0.80 a 0.95 dependendo da densidade de tokens)
                token_ratio = len(tokens) / max(len(cand_tokens), 1)
                final_score = max(base_sim, 0.75 + (0.20 * token_ratio))
            else:
                final_score = base_sim

            candidates.append(
                ResearcherCandidate(
                    id=str(r_id),
                    name=name,
                    institution=inst,
                    score=round(final_score, 3),
                    lattes_id=lattes_id,
                )
            )

        # Ordena candidatos por score final decrescente
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates
