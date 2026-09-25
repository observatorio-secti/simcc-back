from unidecode import unidecode


def pagination(page, lenght):
    return f'OFFSET {lenght * (page - 1)} LIMIT {lenght}'


def parse_terms(string_of_terms):
    operator_map = {';': 'AND', '.': 'AND NOT', '|': 'OR', '(': '(', ')': ')'}
    terms = []
    term = ''

    for char in string_of_terms:
        if char in operator_map:
            if term.strip():
                terms.append(term.strip())
                term = ''
            terms.append(operator_map[char])
        else:
            term += char
    if term.strip():
        terms.append(term.strip())
    return terms


def sanitize_terms(terms):
    sanitized = []
    for term in terms:
        if term not in {'AND', 'OR', 'AND NOT', '(', ')'}:
            sanitized.append(unidecode(term.lower()).replace("'", ''))
        else:
            sanitized.append(term)
    return sanitized


# Pesos do ts_rank na ordem {D, C, B, A}: título (A) vale 1.0 e o resumo
# do OpenAlex (B) vale 0.7.
TITLE_ABSTRACT_RANK_WEIGHTS = '{0.1, 0.2, 0.7, 1.0}'


def _tsvector(column):
    return f"""
                to_tsvector(
                translate(
                unaccent(
                LOWER({column})), '-\\.:;''',' '))"""


def build_query_terms(sanitized_terms, column, vector=None, rank_weights=None):
    terms_dict = {}
    query_parts = []
    term_counter = 1
    vector = vector or _tsvector(column)
    weights = f"'{rank_weights}', " if rank_weights else ''

    for term in sanitized_terms:
        if term in {'AND', 'OR', 'AND NOT', '(', ')'}:
            query_parts.append(term)
        else:
            placeholder = f'term{term_counter}'
            terms_dict[placeholder] = term
            SCRIPT_SQL = f"""
                ts_rank({weights}{vector},
                websearch_to_tsquery(%({placeholder})s)) > 0.04
                """
            query_parts.append(SCRIPT_SQL)
            term_counter += 1

    return ' '.join(query_parts), terms_dict


def websearch_filter(column, string_of_terms):
    terms = parse_terms(string_of_terms)
    sanitized_terms = sanitize_terms(terms)
    query_terms, terms_dict = build_query_terms(sanitized_terms, column)

    filter_sql = f' AND ({query_terms})'
    return filter_sql, terms_dict


def openalex_abstract_join(production_alias):
    return (
        'LEFT JOIN openalex_article oa '
        f'ON oa.article_id = {production_alias}.id'
    )


def title_abstract_filter(title_column, abstract_column, string_of_terms):
    """Como `websearch_filter`, mas busca no título concatenado ao resumo
    do OpenAlex, com peso 1.0 para o título e 0.7 para o resumo.

    A query precisa de um LEFT JOIN com `openalex_article` para expor
    `abstract_column` (ver `openalex_abstract_join`); artigos sem resumo
    seguem buscáveis pelo título. Sem `abstract_column`, busca só no título.
    """
    if abstract_column is None:
        return websearch_filter(title_column, string_of_terms)

    abstract_or_empty = f"COALESCE({abstract_column}, '')"
    vector = (
        f"setweight({_tsvector(title_column)}, 'A')"
        f" || setweight({_tsvector(abstract_or_empty)}, 'B')"
    )
    terms = parse_terms(string_of_terms)
    sanitized_terms = sanitize_terms(terms)
    query_terms, terms_dict = build_query_terms(
        sanitized_terms,
        title_column,
        vector=vector,
        rank_weights=TITLE_ABSTRACT_RANK_WEIGHTS,
    )

    filter_sql = f' AND ({query_terms})'
    return filter_sql, terms_dict


def names_filter(column, name):
    name_clean = name.replace('(', '').replace(')', '').replace(';', ' ')
    tokens = [
        unidecode(t.strip().lower()) for t in name_clean.split() if t.strip()
    ]
    if not tokens:
        return '', {}

    conditions = []
    params = {}
    for i, token in enumerate(tokens):
        param_name = f'name_tok_{i}'
        params[param_name] = f'%{token}%'
        conditions.append(f'unaccent(LOWER({column})) LIKE :{param_name}')

    filter_sql = f' AND ({" AND ".join(conditions)})'
    return filter_sql, params
