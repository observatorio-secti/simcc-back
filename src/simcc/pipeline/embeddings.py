"""
embeddings.py — Camada única de embeddings semânticos do pipeline.

Substitui o SentenceTransformer (PyTorch) pelo FastEmbed (ONNX Runtime), que
produz os mesmos vetores a partir do mesmo modelo `paraphrase-multilingual-MiniLM-L12-v2`
sem carregar o PyTorch na imagem.

Contrato exposto (compatível com o uso que o pipeline fazia do SentenceTransformer):
    model = get_embedding_model(settings.embedding_model)
    model.encode(["texto 1", "texto 2"])  -> np.ndarray (n, dim) normalizado

O BERTopic recebe o objeto `EmbeddingModel` diretamente, pois implementa `.encode()`.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import numpy as np
from bertopic.backend import BaseEmbedder
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Mesmo modelo usado antes via SentenceTransformer, agora servido por ONNX.
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Nomes antigos/curtos aceitos por compatibilidade com .env e taxonomies salvas.
_MODEL_ALIASES = {
    "paraphrase-multilingual-MiniLM-L12-v2": DEFAULT_EMBEDDING_MODEL,
    "paraphrase_multilingual_MiniLM_L12_v2": DEFAULT_EMBEDDING_MODEL,
}

_BATCH_SIZE = 64
_MAX_LENGTH = 512


def canonical_model_name(model_name: str | None) -> str:
    """Normaliza o nome do modelo, resolvendo aliases para o id canônico."""
    name = (model_name or DEFAULT_EMBEDDING_MODEL).strip()
    return _MODEL_ALIASES.get(name, name)


def _resolve_cache_dir() -> str | None:
    """
    Diretório de cache dos pesos. Dentro do container é um volume persistente,
    para baixar o modelo uma única vez em vez de a cada boot.
    """
    cache_dir = os.getenv("CLASSIFIER_MODEL_CACHE_DIR")
    if not cache_dir:
        return None
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError as err:
        logger.warning("Não foi possível criar o cache de modelos em %s: %s", cache_dir, err)
        return None
    return cache_dir


class EmbeddingModel(BaseEmbedder):
    """
    Encapsula o TextEmbedding do FastEmbed com a interface usada pelo pipeline.

    Herda de `BaseEmbedder` do BERTopic de propósito: sem isso o BERTopic cai no
    backend SentenceTransformer (que exige PyTorch) ao receber um objeto desconhecido.

    `passage_embed` é usado em ambos os lados das comparações de similaridade.
    Modelos da família e5 exigem prefixos assimétricos ("query: "/"passage: "), mas
    o MiniLM multilíngue usado aqui é simétrico, então um único caminho é correto.
    """

    def __init__(self, model_name: str | None = None) -> None:
        super().__init__()
        self.model_name = canonical_model_name(model_name)
        self.embedding_model = TextEmbedding(
            model_name=self.model_name,
            cache_dir=_resolve_cache_dir(),
        )
        logger.info("Modelo de embeddings carregado: %s", self.model_name)

    def encode(
        self,
        sentences: str | list[str],
        batch_size: int = _BATCH_SIZE,
        max_length: int = _MAX_LENGTH,
        **_: object,
    ) -> np.ndarray:
        """
        Vetoriza textos. Aceita string única ou lista e sempre devolve np.ndarray 2D
        normalizado, igual ao retorno do SentenceTransformer.
        """
        single = isinstance(sentences, str)
        texts = [sentences] if single else list(sentences)

        if not texts:
            raise ValueError("encode() requer ao menos um texto.")

        vectors = np.asarray(
            list(
                self.embedding_model.passage_embed(
                    texts,
                    batch_size=batch_size,
                    max_length=max_length,
                )
            ),
            dtype=np.float32,
        )
        return vectors[0] if single else vectors

    def embed(self, documents: list[str], verbose: bool = False) -> np.ndarray:
        """Interface exigida pelo BERTopic (BaseEmbedder)."""
        vectors = np.asarray(
            list(
                self.embedding_model.passage_embed(
                    list(documents),
                    batch_size=_BATCH_SIZE,
                    show_progress_bar=verbose,
                )
            ),
            dtype=np.float32,
        )
        logger.info("Embeddings gerados: %d textos -> %s", len(documents), vectors.shape)
        return vectors


@lru_cache(maxsize=2)
def get_embedding_model(model_name: str | None = None) -> EmbeddingModel:
    """
    Cacheia o modelo por nome. O pipeline o carrega em três etapas seguidas
    (document_loader, topic_modeling, graph_topic_integrator); sem este cache
    o mesmo pesos seria instanciado três vezes no mesmo run.
    """
    return EmbeddingModel(model_name)
