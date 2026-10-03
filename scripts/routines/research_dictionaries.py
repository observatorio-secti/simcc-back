import html
import re
import unicodedata
from collections import Counter

import nltk
from sqlalchemy import text

from simcc.core.db.database import get_sync_session
from simcc.core.logging import logger
from simcc.core.logging.events import (
    routine_step_finished,
    routine_step_started,
)

MAX_NGRAM = 4
MIN_FREQUENCY = 5
MIN_UNIGRAM_LENGTH = 4
MAX_TERM_LENGTH = 255
# Fragmento é descartado se um n-grama maior responde por esta fração dele
NESTED_RATIO = 0.9
FETCH_BATCH = 5000
INSERT_BATCH = 5000

# Pontuação e hífen solto (" - ") encerram um segmento: n-gramas não os cruzam
SEGMENT_BREAK = re.compile(r"[^\w\s'’-]+|\s-+\s")
TOKEN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
HAS_DIGIT = re.compile(r'\d')

# Conectivos ausentes das listas do NLTK e artigos/preposições do espanhol
EXTRA_STOPWORDS = (
    'sobre', 'após', 'através', 'partir', 'desde', 'durante',
    'el', 'la', 'los', 'las', 'en', 'del', 'y', 'un', 'una', 'con',
    'su', 'sus', 'al', 'lo',
)  # fmt: skip

SOURCES = [
    (
        'ARTICLE',
        """
        SELECT DISTINCT title FROM bibliographic_production
        WHERE type = 'ARTICLE' AND title IS NOT NULL
        """,
    ),
    (
        'BOOK_CHAPTER',
        """
        SELECT DISTINCT title FROM bibliographic_production
        WHERE type = 'BOOK_CHAPTER' AND title IS NOT NULL
        """,
    ),
    (
        'PATENT',
        'SELECT DISTINCT title FROM patent WHERE title IS NOT NULL',
    ),
    (
        'SPEAKER',
        """
        SELECT DISTINCT title FROM participation_events
        WHERE title IS NOT NULL
        """,
    ),
    (
        'ABSTRACT',
        """
        SELECT DISTINCT abstract FROM researcher
        WHERE abstract IS NOT NULL
        """,
    ),
    (
        'BOOK',
        """
        SELECT DISTINCT title FROM bibliographic_production
        WHERE type = 'BOOK' AND title IS NOT NULL
        """,
    ),
]

INSERT_SQL = """
    INSERT INTO research_dictionary (term, frequency, type_)
    VALUES (:term, :frequency, :type_)
"""


def strip_accents(value: str) -> str:
    if value.isascii():
        return value
    return ''.join(
        char
        for char in unicodedata.normalize('NFKD', value)
        if not unicodedata.combining(char)
    )


def get_stopwords() -> frozenset[str]:
    stopwords = nltk.corpus.stopwords.words('english')
    stopwords.extend(nltk.corpus.stopwords.words('portuguese'))
    stopwords.extend(EXTRA_STOPWORDS)
    return frozenset(strip_accents(word.lower()) for word in stopwords)


def iter_runs(content: str):
    """Sequências de tokens contíguos, sem pontuação ou números no meio."""
    # Títulos do Lattes trazem entidades HTML (&quot;, &amp;)
    content = html.unescape(content).lower()
    for segment in SEGMENT_BREAK.split(content):
        run = []
        for token in TOKEN.findall(segment):
            if HAS_DIGIT.search(token):
                if run:
                    yield run
                run = []
            else:
                run.append(token)
        if run:
            yield run


def extract_terms(
    content: str, stopwords: frozenset[str], max_n: int = MAX_NGRAM
) -> set[str]:
    """N-gramas (1..max_n) do texto que não começam nem terminam em stopword.

    Stopwords no meio são mantidas ("qualidade de vida").
    """
    terms = set()
    for tokens in iter_runs(content):
        is_stopword = [strip_accents(token) in stopwords for token in tokens]
        for start in range(len(tokens)):
            if is_stopword[start]:
                continue
            stop = min(start + max_n, len(tokens))
            for end in range(start, stop):
                if not is_stopword[end]:
                    terms.add(' '.join(tokens[start : end + 1]))
    return terms


def merge_variants(counts: Counter) -> tuple[Counter, dict[str, str]]:
    """Soma variantes que só diferem na acentuação e elege a mais frequente."""
    totals = Counter()
    display = {}
    for term, frequency in counts.items():
        key = strip_accents(term)
        totals[key] += frequency
        current = display.get(key)
        if current is None or (frequency, term) > (counts[current], current):
            display[key] = term
    return totals, display


def find_nested(frequent: dict[str, int], stopwords: frozenset) -> set[str]:
    """Fragmentos que quase só ocorrem dentro de um n-grama maior.

    Ex.: "programa de pós" diante de "programa de pós graduação".
    """
    largest_container = {}
    for key, frequency in frequent.items():
        tokens = key.split(' ')
        for size in range(2, len(tokens)):
            for start in range(len(tokens) - size + 1):
                part = tokens[start : start + size]
                if part[0] in stopwords or part[-1] in stopwords:
                    continue
                part = ' '.join(part)
                if frequency > largest_container.get(part, 0):
                    largest_container[part] = frequency

    return {
        part
        for part, frequency in largest_container.items()
        if frequency >= NESTED_RATIO * frequent.get(part, frequency)
    }


def build_dictionary(
    contents, stopwords: frozenset[str]
) -> list[tuple[str, int]]:
    """Termos e respectiva quantidade de textos em que aparecem."""
    counts = Counter()
    for content in contents:
        counts.update(extract_terms(content, stopwords))

    totals, display = merge_variants(counts)
    del counts
    frequent = {
        key: frequency
        for key, frequency in totals.items()
        if frequency >= MIN_FREQUENCY
    }
    del totals
    nested = find_nested(frequent, stopwords)

    dictionary = []
    for key, frequency in frequent.items():
        if len(key) >= MAX_TERM_LENGTH or key in nested:
            continue
        if ' ' not in key and len(key) < MIN_UNIGRAM_LENGTH:
            continue
        dictionary.append((display[key], frequency))

    dictionary.sort(key=lambda item: (-item[1], item[0]))
    return dictionary


def fetch_contents(session, query: str):
    result = session.execute(
        text(query).execution_options(yield_per=FETCH_BATCH)
    )
    return result.scalars()


def replace_dictionary(session, doc_type: str, dictionary) -> None:
    session.execute(
        text('DELETE FROM research_dictionary WHERE type_ = :type_'),
        {'type_': doc_type},
    )
    for offset in range(0, len(dictionary), INSERT_BATCH):
        session.execute(
            text(INSERT_SQL),
            [
                {'term': term, 'frequency': frequency, 'type_': doc_type}
                for term, frequency in dictionary[
                    offset : offset + INSERT_BATCH
                ]
            ],
        )


items_found = 0
items_succeeded = 0
items_failed = 0


def main():
    global items_found, items_succeeded, items_failed
    session = next(get_sync_session())
    items_found = len(SOURCES)

    try:
        stopwords = get_stopwords()

        for doc_type, query in SOURCES:
            step = f'dictionary_{doc_type.lower()}'
            routine_step_started(step)
            dictionary = build_dictionary(
                fetch_contents(session, query), stopwords
            )
            replace_dictionary(session, doc_type, dictionary)
            routine_step_finished(step)
            items_succeeded += 1

        session.commit()
        items_failed = items_found - items_succeeded
    except Exception as e:
        items_failed = items_found - items_succeeded
        logger.error(f'Error in research_dictionaries: {e}')
        session.rollback()
        raise e


if __name__ == '__main__':
    main()
