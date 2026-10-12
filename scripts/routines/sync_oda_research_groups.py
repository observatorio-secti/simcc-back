import asyncio
import os
import time

import httpx
import polars as pl

from simcc.core.logging import logger
from simcc.core.logging.events import (
    routine_item_error,
    routine_progress,
    routine_step_finished,
    routine_step_started,
)
from simcc.core.settings import Settings

SETTINGS = Settings()
PAGE_SIZE = 500
CONCURRENCY = 10
MAX_RETRIES = 3
TIMEOUT = httpx.Timeout(60.0)

SCHEMA = {
    'oda_id': pl.Utf8,
    'dgp_id': pl.Utf8,
    'name': pl.Utf8,
    'area': pl.Utf8,
    'year': pl.Int32,
    'situation': pl.Utf8,
    'institution_acronym': pl.Utf8,
    'institution_name': pl.Utf8,
    'leaders': pl.List(pl.Struct({'name': pl.Utf8, 'lattes_id': pl.Utf8})),
}

items_found = 0
items_succeeded = 0
items_failed = 0


async def get_json(client, path, params=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(2**attempt)


async def fetch_groups(client):
    groups = []
    page = 1
    while True:
        data = await get_json(
            client,
            '/grupos-pesquisa/simcc',
            {'page': page, 'size': PAGE_SIZE},
        )
        groups.extend(data['data'])
        if page >= data['meta']['totalPages']:
            return groups
        page += 1


async def fetch_leaders(client, semaphore, group_id):
    async with semaphore:
        data = await get_json(
            client,
            f'/grupos-pesquisa/{group_id}/pesquisadores',
            {'eLider': 'true', 'size': 30},
        )
    return [
        {'name': member.get('nome'), 'lattes_id': member.get('lattesId')}
        for member in data['data']
    ]


def headquarters(group):
    institutions = group.get('instituicoes') or []
    for institution in institutions:
        if institution.get('tipoRelacao') == 'SEDE':
            return institution
    return institutions[0] if institutions else {}


def build_record(group, leaders):
    institution = headquarters(group)
    return {
        'oda_id': group['id'],
        'dgp_id': group.get('dgpId'),
        'name': group.get('nome'),
        'area': group.get('areaPredominante'),
        'year': group.get('anoFormacao'),
        'situation': group.get('situacao'),
        'institution_acronym': institution.get('sigla'),
        'institution_name': institution.get('nome'),
        'leaders': leaders,
    }


async def sync():
    global items_found, items_succeeded, items_failed

    async with httpx.AsyncClient(
        base_url=SETTINGS.ODA_API_URL, timeout=TIMEOUT
    ) as client:
        routine_step_started('fetch_oda_research_groups')
        groups = await fetch_groups(client)
        items_found = len(groups)
        routine_step_finished(
            'fetch_oda_research_groups', total_found=items_found
        )

        routine_step_started('fetch_oda_research_group_leaders')
        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [
            fetch_leaders(client, semaphore, group['id']) for group in groups
        ]
        records = []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, (group, result) in enumerate(zip(groups, results)):
            leaders = result
            if isinstance(result, Exception):
                items_failed += 1
                routine_item_error(
                    group['id'],
                    'Falha ao buscar líderes do grupo na ODA',
                    detail=str(result),
                )
                leaders = []
            else:
                items_succeeded += 1
            records.append(build_record(group, leaders))

            if (idx + 1) % 250 == 0 or (idx + 1) == items_found:
                routine_progress(
                    'fetch_oda_research_group_leaders',
                    idx + 1,
                    items_found,
                    items_succeeded,
                    items_failed,
                )
        routine_step_finished(
            'fetch_oda_research_group_leaders',
            total_processed=items_succeeded,
        )

    return records


def save(records):
    path = SETTINGS.ODA_RESEARCH_GROUPS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f'{path}.tmp'
    pl.DataFrame(records, schema=SCHEMA).write_parquet(tmp_path)
    os.replace(tmp_path, path)


def main():
    try:
        records = asyncio.run(sync())
    except Exception as e:
        logger.error(f'Error in sync_oda_research_groups: {e}')
        raise e

    if not records:
        raise RuntimeError('ODA não retornou grupos de pesquisa')

    routine_step_started('save_oda_research_groups')
    start_time = time.perf_counter()
    save(records)
    routine_step_finished(
        'save_oda_research_groups',
        duration=time.perf_counter() - start_time,
        total_saved=len(records),
    )


if __name__ == '__main__':
    main()
