import io
import os
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import httpx
import polars as pl
from sqlalchemy import text
from zeep import Client
from zeep.transports import Transport

from simcc.core.db.database import get_sync_session
from simcc.core.logging import logger
from simcc.core.logging.context import routine_name_ctx
from simcc.core.logging.events import (
    routine_item_error,
    routine_progress,
    routine_step_finished,
    routine_step_started,
)
from simcc.core.settings import Settings

SETTINGS = Settings()

XML_PATH = SETTINGS.XML_PATH
CURRENT_XML_PATH = SETTINGS.CURRENT_XML_PATH
ZIP_XML_PATH = SETTINGS.ZIP_XML_PATH
PROXY = SETTINGS.ALTERNATIVE_CNPQ_SERVICE

MAX_RETRIES = 3
MAX_PARALLEL_DOWNLOADS = 5
MAX_PARALLEL_CHECKS = 10
HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

AUTH_TOKEN_URL = 'http://localhost:8009/auth/token'
EXPORT_PARQUET_URL = ('http://localhost:8009/academic/researchers/export/parquet')  # fmt: skip  # ruff: ignore[line-too-long]

ADMIN_USERNAME: str = 'admin'
ADMIN_EMAIL: str = 'admin@simcc.org'
ADMIN_PASSWORD: str = 'admin_secret_password'

_zeep_client = None


def get_zeep_client():
    global _zeep_client
    if _zeep_client is None and not PROXY:
        _zeep_client = Client(
            'http://servicosweb.cnpq.br/srvcurriculo/WSCurriculo?wsdl',
            transport=Transport(timeout=30, operation_timeout=30),
        )
    return _zeep_client


def cnpq_att_call(lattes_id):
    if PROXY:
        response = httpx.get(
            f'https://simcc.uesc.br/v3/api/getDataAtualizacaoCV?lattes_id={lattes_id}',
            verify=False,
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    client = get_zeep_client()
    return client.service.getDataAtualizacaoCV(lattes_id)


def cnpq_att(lattes_id):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            data = cnpq_att_call(lattes_id)
            if not data:
                return datetime.min, None
            return datetime.strptime(data, '%d/%m/%Y %H:%M:%S'), None
        except Exception as e:
            last_err = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
    return (
        None,
        f'Falha ao consultar data CNPq após {MAX_RETRIES} tentativas: {last_err}',
    )


def get_db_dates_map():
    session = None
    try:
        session = next(get_sync_session())
        result = (
            session
            .execute(
                text(
                    'SELECT lattes_id, last_update FROM researcher WHERE lattes_id IS NOT NULL'
                )
            )
            .mappings()
            .all()
        )
        return {
            str(row['lattes_id']).strip().zfill(16): row['last_update']
            for row in result
            if row['lattes_id']
        }
    finally:
        if session is not None:
            session.close()


def check_researcher_status(record, db_dates):
    lattes_id = record['lattes_id']
    researcher_id = record['researcher_id']
    name = record['name']

    cnpq_date, cnpq_err = cnpq_att(lattes_id)
    if cnpq_err:
        return False, record, cnpq_err

    db_date = db_dates.get(lattes_id)
    if db_date is None:
        db_date = datetime.min

    if cnpq_date <= db_date:
        cnpq_str = (
            cnpq_date.strftime('%d/%m/%Y %H:%M:%S')
            if cnpq_date != datetime.min
            else 'Sem data'
        )
        db_str = (
            db_date.strftime('%d/%m/%Y %H:%M:%S')
            if db_date != datetime.min
            else 'Sem data'
        )
        return (
            False,
            record,
            f'Atualizado no banco (CNPq: {cnpq_str} <= Banco: {db_str})',
        )

    return True, record, None


def download_single_xml(record):
    lattes_id = record['lattes_id']
    researcher_id = record['researcher_id']
    name = record['name']

    try:
        if PROXY:
            response = httpx.get(
                f'https://simcc.uesc.br/v3/api/getCurriculoCompactado?lattes_id={lattes_id}',
                verify=False,
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            content = response.content
        else:
            client = get_zeep_client()
            content = client.service.getCurriculoCompactado(lattes_id)

        if not content:
            return False, 'Conteúdo retornado pelo serviço está vazio'
    except Exception as e:
        return False, f'Falha na requisição do arquivo: {e}'

    try:
        zip_path = os.path.join(ZIP_XML_PATH, f'{lattes_id}.zip')

        os.makedirs(ZIP_XML_PATH, exist_ok=True)
        os.makedirs(XML_PATH, exist_ok=True)
        os.makedirs(CURRENT_XML_PATH, exist_ok=True)

        with open(zip_path, 'wb') as f:
            f.write(content)

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(XML_PATH)
            z.extractall(CURRENT_XML_PATH)

        if os.path.exists(zip_path):
            os.remove(zip_path)

        return True, 'XML extraído'
    except Exception as e:
        return False, f'Falha ao extrair arquivo: {e}'


def get_auth_token():
    payload = {
        'grant_type': 'password',
        'username': ADMIN_USERNAME,
        'password': ADMIN_PASSWORD,
        'scope': '',
        'client_id': '',
        'client_secret': '',
    }
    headers = {
        'accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    response = httpx.post(
        AUTH_TOKEN_URL,
        data=payload,
        headers=headers,
        timeout=15.0,
    )
    response.raise_for_status()
    data = response.json()
    return data['access_token']


def fetch_researchers():
    token = get_auth_token()
    headers = {
        'Authorization': f'Bearer {token}',
    }

    response = httpx.get(
        EXPORT_PARQUET_URL,
        headers=headers,
        timeout=60.0,
    )
    response.raise_for_status()

    df = pl.read_parquet(io.BytesIO(response.content))

    if 'lattes_id' not in df.columns:
        raise ValueError(
            "Coluna obrigatória 'lattes_id' ausente no arquivo Parquet."
        )

    if 'researcher_id' not in df.columns:
        if 'id' in df.columns:
            df = df.with_columns(pl.col('id').alias('researcher_id'))
        else:
            df = df.with_columns(
                pl.int_range(0, pl.len()).cast(pl.Utf8).alias('researcher_id')
            )

    if 'name' not in df.columns:
        df = df.with_columns(pl.lit('Desconhecido').alias('name'))

    df = (
        df
        .filter(pl.col('lattes_id').is_not_null())
        .with_columns([
            pl.col('researcher_id').cast(pl.Utf8),
            pl.col('name').fill_null('Desconhecido').cast(pl.Utf8),
            pl.col('lattes_id').cast(pl.Utf8).str.strip_chars().str.zfill(16),
        ])
        .filter(pl.col('lattes_id') != '0' * 16)
    )

    return df


def filter_outdated_researchers(researchers_df):
    records = researchers_df.to_dicts()
    total = len(records)
    if total == 0:
        return []

    try:
        db_dates = get_db_dates_map()
    except Exception as e:
        logger.error(f'Falha ao consultar datas no banco local: {e}')
        raise

    routine_step_started('check_cnpq_updates', total_items=total)

    outdated = []
    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CHECKS) as executor:
        futures = {
            executor.submit(check_researcher_status, record, db_dates): record
            for record in records
        }

        for future in as_completed(futures):
            completed += 1
            is_outdated, record, reason = future.result()

            if is_outdated:
                outdated.append(record)
            elif reason and not reason.startswith('Atualizado no banco'):
                routine_item_error(
                    record['researcher_id'],
                    f'ERRO CHECAGEM: {reason}',
                    name=record['name'],
                    lattes_id=record['lattes_id'],
                )

            if completed % 50 == 0 or completed == total:
                routine_progress(
                    'check_cnpq_updates',
                    completed,
                    total,
                    len(outdated),
                    completed - len(outdated),
                )

    routine_step_finished('check_cnpq_updates', total_items=total)
    return outdated


def download_lattes(researchers_list):
    total = len(researchers_list)
    if total == 0:
        logger.info('Nenhum pesquisador necessita de atualização.')
        return

    if os.path.exists(XML_PATH):
        for file in os.listdir(XML_PATH):
            path = os.path.join(XML_PATH, file)
            if os.path.isfile(path) and file.endswith('.xml'):
                try:
                    os.remove(path)
                except Exception:
                    pass
    else:
        os.makedirs(XML_PATH, exist_ok=True)

    routine_step_started('download_cnpq_lattes', total_items=total)

    succeeded = 0
    failed = 0
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS) as executor:
        futures = {
            executor.submit(download_single_xml, record): record
            for record in researchers_list
        }

        for future in as_completed(futures):
            completed += 1
            record = futures[future]
            res_id = record['researcher_id']
            name = record['name']
            lattes_id = record['lattes_id']

            try:
                success, detail = future.result()
                if success:
                    succeeded += 1
                    msg = f'[OK] [{completed}/{total}] {name} ({lattes_id}): {detail}'
                    logger.debug(msg)
                else:
                    failed += 1
                    routine_item_error(
                        res_id,
                        f'NÃO BAIXADO: {detail}',
                        name=name,
                        lattes_id=lattes_id,
                    )
            except Exception as e:
                failed += 1
                routine_item_error(
                    res_id,
                    f'ERRO PROCESSAMENTO: {e}',
                    name=name,
                    lattes_id=lattes_id,
                )

            if completed % 20 == 0 or completed == total:
                routine_progress(
                    'download_cnpq_lattes',
                    completed,
                    total,
                    succeeded,
                    failed,
                )

    routine_step_finished('download_cnpq_lattes', total_items=total)


def main():
    if not routine_name_ctx.get():
        routine_name_ctx.set('soap_lattes')

    start_time = datetime.now()
    msg = f'[INÍCIO] Rotina soap_lattes iniciada em {start_time.strftime("%Y-%m-%d %H:%M:%S")}'
    logger.info(msg)

    try:
        researchers = fetch_researchers()
        msg = f'{len(researchers)} pesquisadores carregados do endpoint.'
        logger.info(msg)

        outdated_researchers = filter_outdated_researchers(researchers)
        msg = f'{len(outdated_researchers)} pesquisadores identificados como desatualizados.'
        logger.info(msg)

        download_lattes(outdated_researchers)

        end_time = datetime.now()
        duration_str = str(end_time - start_time).split('.')[0]
        msg = f'[FIM] Rotina soap_lattes finalizada em {end_time.strftime("%Y-%m-%d %H:%M:%S")} (Duração: {duration_str})'
        logger.info(msg)

    except Exception as e:
        end_time = datetime.now()
        msg = f'[INTERROMPIDO] Rotina soap_lattes finalizada com erro em {end_time.strftime("%Y-%m-%d %H:%M:%S")}: {e}'
        logger.error(msg)
        raise


if __name__ == '__main__':
    main()
