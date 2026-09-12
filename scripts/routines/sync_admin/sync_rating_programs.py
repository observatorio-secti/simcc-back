import os
import re
import unicodedata
from collections import Counter

import polars as pl
from sqlalchemy import text

from simcc.core.db.database import get_admin_sync_session
from simcc.core.logging import logger
from simcc.core.logging.events import (
    routine_item_error,
    routine_progress,
    routine_step_finished,
    routine_step_started,
)


def normalize_string(s):
    if not isinstance(s, str):
        return str(s) if s is not None else ''
    s = unicodedata.normalize('NFD', s).replace('\n', '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower()


def clean_code(code):
    if not code:
        return ''
    return re.sub(r'[^A-Za-z0-9]', '', str(code)).upper()


def load_rating_programs_csv(path='storage/seed/rating_programs.csv'):
    if not os.path.exists(path):
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..')
        )
        alt_path = os.path.join(project_root, path)
        if os.path.exists(alt_path):
            path = alt_path

    df = pl.read_csv(path)
    df = df.rename({col: normalize_string(col) for col in df.columns})
    return df


def get_programs_mapping(session):
    sql = text(
        'SELECT graduate_program_id::TEXT, code '
        'FROM graduate_program WHERE code IS NOT NULL'
    )
    result = session.execute(sql).mappings().all()
    return {
        clean_code(row['code']): row['graduate_program_id']
        for row in result
        if clean_code(row['code'])
    }


def process_rating_row(row, programs_map):
    raw_code = row.get('code')
    rating = row.get('rating')

    code = clean_code(raw_code)
    if not code:
        return None, 'Erro: Código do programa vazio ou ausente'

    if not rating or not str(rating).strip():
        rating_str = 'Não informado'
    else:
        rating_str = str(rating).strip()

    if code not in programs_map:
        return None, 'Ignorado: Programa não cadastrado no banco'

    return {
        'code': code,
        'rating': rating_str,
    }, None


def _process_records(records, programs_map, total_rows):
    stats = Counter()
    valid_ratings = []

    for idx, row_dict in enumerate(records):
        rating_data, error_reason = process_rating_row(row_dict, programs_map)

        if rating_data:
            valid_ratings.append(rating_data)
            stats['Sucesso'] += 1
        else:
            stats[error_reason] += 1
            if 'Erro' in error_reason:
                pg_code = row_dict.get('code')
                routine_item_error(str(pg_code), error_reason)

        if (idx + 1) % 50 == 0 or (idx + 1) == total_rows:
            routine_progress(
                'process_rating_programs_csv',
                idx + 1,
                total_rows,
                stats['Sucesso'],
                total_rows - stats['Sucesso'],
            )

    return valid_ratings, stats['Sucesso'], total_rows - stats['Sucesso']


items_found = 0
items_succeeded = 0
items_failed = 0


def main(session=None, csv_path='storage/seed/rating_programs.csv'):
    global items_found, items_succeeded, items_failed  # noqa: PLW0603
    if session is None:
        session = next(get_admin_sync_session())

    try:  # noqa: PLW0717
        routine_step_started('process_rating_programs_csv')
        ratings_df = load_rating_programs_csv(csv_path)

        required_cols = {'code', 'rating'}
        missing = required_cols - set(ratings_df.columns)
        if missing:
            items_found = len(ratings_df)
            items_succeeded = 0
            items_failed = items_found
            err_msg = f'Colunas obrigatórias ausentes no CSV: {missing}'
            logger.error(err_msg)
            raise ValueError(err_msg)

        programs_map = get_programs_mapping(session)
        total_rows = len(ratings_df)
        items_found = total_rows

        valid_ratings, items_succeeded, items_failed = _process_records(
            ratings_df.to_dicts(), programs_map, total_rows
        )

        routine_step_finished(
            'process_rating_programs_csv',
            total_valid=items_succeeded,
            total_invalid=items_failed,
        )

        if valid_ratings:
            routine_step_started('update_graduate_program_ratings')
            query_update = text("""
                UPDATE public.graduate_program
                SET rating = :rating
                WHERE code = :code;
            """)
            session.execute(query_update, valid_ratings)
            routine_step_finished(
                'update_graduate_program_ratings',
                total_records=len(valid_ratings),
            )

        session.commit()
    except Exception as e:
        items_failed = items_found - items_succeeded
        logger.error(
            f'Erro na execução da rotina sync_rating_programs: {str(e)}'
        )
        session.rollback()
        raise e


if __name__ == '__main__':
    main()
