from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClarificationType(str, Enum):
    RESEARCHER_DISAMBIGUATION = 'researcher_disambiguation'
    PRODUCTION_TYPE_SELECTION = 'production_type_selection'
    TIME_PERIOD_SELECTION = 'time_period_selection'
    INSTITUTION_SELECTION = 'institution_selection'


class ClarificationOption(BaseModel):
    id: str = Field(
        description='Identificador único da opção (ex: researcher_id)'
    )
    label: str = Field(
        description='Texto principal exibido no botão/card (ex: Nome do Pesquisador)'
    )
    description: Optional[str] = Field(
        None,
        description="Contexto secundário (ex: 'UNEB · Ciência da Computação')",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description='Dados adicionais para a UI'
    )


class ClarificationPayload(BaseModel):
    type: ClarificationType
    question: str
    field_to_bind: str
    options: List[ClarificationOption]
    original_query: str
    context: Dict[str, Any] = Field(default_factory=dict)


class ClarificationResponse(BaseModel):
    field: str = Field(
        description="Campo que foi resolvido (ex: 'researcher_id')"
    )
    value: str = Field(
        description='Valor selecionado pelo usuário (ex: uuid do pesquisador)'
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description='Metadados opcionais da seleção'
    )
