"""Importa docentes usando o formato fixo de cada instituicao."""

import argparse
import asyncio
import csv
import re
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from unidecode import unidecode

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TERRITORIES = ROOT / 'storage/powerBI/dim_territorio_identidade.csv'
INSTITUTION_FORMATS = {
    'EBMSP': {
        'header_row': 1,
        'delimiter': ';',
        'columns': {
            'name': 'NOME_DOCENTE',
            'lattes_id': 'lattes_id',
            'workload': 'CH semanal',
            'zip_code': 'CEP',
        },
    },
    'UFOB': {
        'header_row': 1,
        'delimiter': ';',
        'columns': {
            'name': 'NOME SERVIDOR',
            'lattes_id': 'lattes_id',
            'workload': 'JORNADA TRABALHO',
            'zip_code': 'CEP',
        },
        'workloads': {
            '20 h sem': '20',
            '40 h sem': '40',
            'Dedc exclus': '40',
            'de': '40',
            'dedicacao exclusiva': '40',
        },
    },
    'UFRB': {
        'header_row': 1,
        'delimiter': ',',
        'columns': {
            'name': 'name',
            'lattes_id': 'lattes_id',
            'workload': 'work_regime',
            'zip_code': 'zip_code',
            'city': 'city',
        },
        'workloads': {
            '20': '20',
            '40': '40',
            'de': '40',
            'dedicacao exclusiva': '40',
        },
    },
}
DEFAULT_BATCH = [
    ('EBMSP', ROOT / 'storage/researchers/ebmsp.csv'),
    ('UFOB', ROOT / 'storage/researchers/ufob.csv'),
    ('UFRB', ROOT / 'storage/researchers/ufrb.csv'),
]
MAX_WEEKLY_HOURS = 168
CEP_LENGTH = 8
LATTES_LENGTH = 16
ALIASES = {
    'nome_docente': 'name',
    'nome_servidor': 'name',
    'nome': 'name',
    'ch_semanal': 'workload',
    'jornada_trabalho': 'workload',
    'work_regime': 'workload',
    'carga_horaria': 'workload',
    'carga_horaria_semanal': 'workload',
    'workload_hours_weekly': 'workload',
    'cep': 'zip_code',
    'territorio_de_identidade': 'identity_territory',
    'territorio_identidade': 'identity_territory',
}


def normalized(value) -> str:
    return ' '.join(unidecode(str(value or '')).casefold().split())


def cell_text(value) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def normalize_lattes_id(value: str) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r'\D', '', str(value))
    if not cleaned:
        return None
    if len(cleaned) <= LATTES_LENGTH:
        return cleaned.zfill(LATTES_LENGTH)
    return None


def read_rows(
    path: Path, header_row: int = 1, delimiter: str | None = None
) -> list[dict]:
    if path.suffix.lower() == '.csv':
        for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
            try:
                content = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError('Nao foi possivel ler o encoding do CSV.')
        stream = StringIO(content)
        for _ in range(header_row - 1):
            stream.readline()
        start = stream.tell()
        sample = stream.read(8192)
        if not sample.strip():
            return []
        if delimiter:
            stream.seek(start)
            return list(csv.DictReader(stream, delimiter=delimiter))
        dialect = csv.Sniffer().sniff(sample, delimiters=';,\t')
        stream.seek(start)
        return list(csv.DictReader(stream, dialect=dialect))
    if path.suffix.lower() != '.xlsx':
        raise ValueError('Use um arquivo .csv ou Excel .xlsx.')
    try:
        from openpyxl import load_workbook  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            'Para ler .xlsx, instale openpyxl: poetry add openpyxl'
        ) from exc
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.worksheets[0]
        values = worksheet.iter_rows(min_row=header_row, values_only=True)
        headers = next(values, ())
        return [dict(zip(headers, row, strict=True)) for row in values]
    finally:
        workbook.close()


def read_institution_rows(path: Path, acronym: str) -> list[dict]:
    profile = INSTITUTION_FORMATS[acronym]
    rows = read_rows(path, profile['header_row'], profile.get('delimiter'))
    columns = profile['columns']
    result = []
    for line, raw in enumerate(rows, start=profile['header_row'] + 1):
        if not any(cell_text(value) for value in raw.values()):
            continue
        source = {normalized(key): value for key, value in raw.items()}
        missing = [
            key for key in columns.values() if normalized(key) not in source
        ]
        if missing:
            raise ValueError(f'Formato {acronym}: colunas ausentes: {missing}')
        row = {
            field: cell_text(source[normalized(column)])
            for field, column in columns.items()
        }
        workload_mappings = {
            normalized(k): str(v)
            for k, v in profile.get('workloads', {}).items()
        }
        raw_workload = row['workload']
        row['workload'] = workload_mappings.get(
            normalized(raw_workload), raw_workload
        )
        row['identity_territory'] = cell_text(
            source.get('territorio_identidade')
            or source.get('territorio_de_identidade')
            or source.get('identity_territory')
        )
        if 'city' in profile['columns']:
            row['city_raw'] = cell_text(
                source.get(normalized(profile['columns']['city']))
            )
        row['_line'] = line
        result.append(row)
    return result


def report_path(acronym: str) -> Path:
    return (
        ROOT
        / 'storage'
        / 'researchers'
        / f'teacher_import_report_{acronym}.csv'
    )


def normalize_row(row: dict) -> dict:
    result = {}
    for key, value in row.items():
        if key is None:
            raise ValueError('Linha com mais valores que colunas.')
        header = re.sub(r'[^a-z0-9]+', '_', normalized(key)).strip('_')
        header = ALIASES.get(header, header)
        if header in result:
            raise ValueError(f'Coluna repetida: {header}')
        result[header] = cell_text(value)
    return result


def parse_workload(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        hours = Decimal(value.replace(',', '.'))
    except InvalidOperation:
        return None
    if (
        not hours.is_finite()
        or not 0 <= hours <= MAX_WEEKLY_HOURS
        or hours != hours.quantize(Decimal('0.01'))
    ):
        return None
    return hours


def normalize_cep(value: str) -> str | None:
    if not value:
        return None
    digits = re.sub(r'[.\s-]', '', value)
    if digits.isascii() and digits.isdigit():
        digits = digits.zfill(CEP_LENGTH)
    if not re.fullmatch(r'[0-9]{8}', digits):
        return None
    return digits


def load_territories(path: Path) -> dict[str, str]:
    result = {}
    for raw in read_rows(path):
        row = normalize_row(raw)
        city = normalized(row.get('municipio'))
        territory = row.get('territorio')
        if not city or not territory:
            continue
        result[city] = territory
    return result


class CepResolver:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.cache = {}

    async def fetch(self, cep: str) -> dict:
        response = await self.client.get(
            f'https://viacep.com.br/ws/{cep}/json/'
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get('erro'):
            raise ValueError('CEP nao encontrado ou resposta invalida.')
        if (
            not isinstance(data.get('localidade'), str)
            or not data['localidade'].strip()
            or not isinstance(data.get('uf'), str)
            or not re.fullmatch(r'[A-Z]{2}', data['uf'])
        ):
            raise ValueError('CEP nao encontrado ou resposta invalida.')
        return data

    async def resolve(self, cep: str) -> dict:
        if cep not in self.cache:
            try:
                self.cache[cep] = await self.fetch(cep)
            except (httpx.HTTPError, ValueError) as exc:
                self.cache[cep] = ValueError(
                    'Nao foi possivel resolver o CEP.'
                )
                raise self.cache[cep] from exc
            finally:
                await asyncio.sleep(0.05)
        if isinstance(self.cache[cep], Exception):
            raise self.cache[cep]
        return self.cache[cep]


async def resolve_institution(session, acronym: str):
    result = await session.execute(
        text(
            'SELECT id, name, acronym FROM institution '
            'WHERE upper(trim(acronym)) = :acronym'
        ),
        {'acronym': acronym.upper()},
    )
    matches = [
        row
        for row in result.mappings().all()
        if normalized(row['acronym']) == normalized(acronym)
    ]
    if len(matches) != 1:
        raise ValueError(
            f'Instituicao {acronym} nao encontrada ou sigla ambigua no banco.'
        )
    return matches[0]['id']


def researcher_indexes(researchers: list) -> dict:
    indexes = {
        key: defaultdict(list)
        for key in ('researcher_id', 'lattes_id', 'name')
    }
    for researcher in researchers:
        indexes['researcher_id'][str(researcher['id'])].append(researcher)
        if researcher.get('lattes_id'):
            lid = normalize_lattes_id(researcher['lattes_id'])
            if lid:
                indexes['lattes_id'][lid].append(researcher)
        if researcher.get('name'):
            indexes['name'][normalized(researcher['name'])].append(researcher)
    return indexes


def match_researcher(row: dict, indexes: dict) -> dict:
    # 1. Tenta por researcher_id direto
    if row.get('researcher_id'):
        rid = str(UUID(row['researcher_id']))
        matches = indexes['researcher_id'].get(rid, [])
        if len(matches) == 1:
            return matches[0]

    # 2. Tenta por lattes_id normalizado (16 digitos)
    lattes_id = normalize_lattes_id(row.get('lattes_id', ''))
    if lattes_id:
        matches = indexes['lattes_id'].get(lattes_id, [])
        if len(matches) == 1:
            return matches[0]

    # 3. Fallback para nome normalizado
    if row.get('name'):
        norm_name = normalized(row['name'])
        matches = indexes['name'].get(norm_name, [])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError('Identificacao ambigua por nome do pesquisador.')

    raise ValueError('Pesquisador nao encontrado no banco de dados.')


async def resolve_city(session, address: dict):
    rows = (
        (
            await session.execute(
                text("""
        SELECT c.id, c.name, c.country_id, s.abbreviation
        FROM city c LEFT JOIN state s ON s.id = c.state_id
        JOIN country country ON country.id = c.country_id
        WHERE upper(s.abbreviation) = :uf
            OR (c.state_id IS NULL AND upper(country.alpha_2_code) = 'BR')
    """),
                {'uf': address['uf']},
            )
        )
        .mappings()
        .all()
    )
    matches = [
        row
        for row in rows
        if normalized(row['name']) == normalized(address['localidade'])
    ]
    if len(matches) != 1:
        raise ValueError('Cidade/UF nao encontrada ou ambigua no banco.')
    return matches[0]


async def resolve_city_by_name(session, city_name: str, uf: str = 'BA'):
    rows = (
        (
            await session.execute(
                text("""
        SELECT c.id, c.name, c.country_id, s.abbreviation
        FROM city c LEFT JOIN state s ON s.id = c.state_id
        JOIN country country ON country.id = c.country_id
        WHERE upper(s.abbreviation) = :uf
    """),
                {'uf': uf.upper()},
            )
        )
        .mappings()
        .all()
    )
    matches = [
        row
        for row in rows
        if normalized(row['name']) == normalized(city_name)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


async def apply_record(session, record: dict, institution_id):
    city_id = record['city']['id'] if record.get('city') else None
    await session.execute(
        text("""
        INSERT INTO researcher_institution (
            researcher_id, institution_id, identity_territory,
            workload, city_id
        ) VALUES (:rid, :iid, :territory, :hours, :city_id)
        ON CONFLICT (researcher_id, institution_id) DO UPDATE SET
            identity_territory = CASE WHEN :update_territory
                THEN EXCLUDED.identity_territory
                ELSE researcher_institution.identity_territory END,
            workload = COALESCE(
                EXCLUDED.workload,
                researcher_institution.workload
            ),
            city_id = COALESCE(
                EXCLUDED.city_id,
                researcher_institution.city_id
            );
    """),
        {
            'rid': record['researcher_id'],
            'iid': institution_id,
            'territory': record['territory'],
            'hours': record['hours'],
            'city_id': city_id,
            'update_territory': record['update_territory'],
        },
    )
    await session.execute(
        text("""
        UPDATE researcher SET institution_id = :iid
        WHERE id = :rid AND institution_id IS NULL
    """),
        {'rid': record['researcher_id'], 'iid': institution_id},
    )


def prepare_record(raw: dict, indexes: dict, institution_id) -> dict:
    row = normalize_row(raw)
    researcher = match_researcher(row, indexes)
    if researcher['institution_id'] not in {None, institution_id}:
        raise ValueError('Pesquisador vinculado a outra universidade.')
    return {
        'researcher_id': researcher['id'],
        'hours': parse_workload(row.get('workload', '')),
        'cep': normalize_cep(row.get('zip_code', '')),
        'territory': row.get('identity_territory') or None,
        'city_raw': row.get('city_raw') or row.get('city'),
        'existing_territory': researcher.get('existing_territory'),
    }


async def enrich_record(session, record: dict, resolver, territories: dict):
    record['city'] = None
    record['update_territory'] = record['territory'] is not None

    if record['cep']:
        try:
            address = await resolver.resolve(record['cep'])
            record['city'] = await resolve_city(session, address)
            if not record['territory'] and address.get('uf') == 'BA':
                record['territory'] = territories.get(
                    normalized(address['localidade'])
                )
        except Exception:
            pass

    if not record['city'] and record.get('city_raw'):
        try:
            record['city'] = await resolve_city_by_name(
                session, record['city_raw']
            )
            if not record['territory']:
                record['territory'] = territories.get(
                    normalized(record['city_raw'])
                )
        except Exception:
            pass

    if record['territory']:
        record['update_territory'] = True


async def import_rows(  # noqa: PLR0913
    session,
    rows: list,
    institution_id,
    resolver: CepResolver,
    territories: dict,
    *,
    dry_run: bool = False,
    acronym: str = 'EBMSP',
) -> list[dict]:
    researchers = (
        (
            await session.execute(
                text("""
        SELECT r.id, r.name, r.lattes_id, r.institution_id,
            ri.identity_territory AS existing_territory
        FROM researcher r
        LEFT JOIN researcher_institution ri ON ri.researcher_id = r.id
            AND ri.institution_id = :institution_id
    """),
                {'institution_id': institution_id},
            )
        )
        .mappings()
        .all()
    )
    indexes = researcher_indexes(researchers)
    report = []
    prepared = defaultdict(list)
    for number, raw in enumerate(rows, start=2):
        item = {
            'linha': raw.get('_line', number),
            'status': 'ignorado',
            'motivo': '',
            'researcher_id': '',
            'universidade': acronym,
            'institution_id': str(institution_id),
            'identity_territory': None,
            'workload': None,
            'city_id': None,
        }
        report.append(item)
        try:
            record = prepare_record(raw, indexes, institution_id)
            item['researcher_id'] = str(record['researcher_id'])
            prepared[record['researcher_id']].append((record, item))
        except ValueError as exc:
            item['motivo'] = str(exc)

    for entries in prepared.values():
        record, item = entries[0]
        if any(other != record for other, _ in entries[1:]):
            for _, entry in entries:
                entry['motivo'] = (
                    'Linhas conflitantes para o mesmo pesquisador.'
                )
            continue
        for _, duplicate in entries[1:]:
            duplicate['motivo'] = 'Linha duplicada.'
        try:
            await enrich_record(session, record, resolver, territories)
            if not dry_run:
                await apply_record(session, record, institution_id)
            item.update({
                'status': 'simulado' if dry_run else 'atualizado',
                'identity_territory': (
                    record['territory']
                    if record['update_territory']
                    else record['existing_territory']
                ),
                'workload': (
                    float(record['hours'])
                    if record['hours'] is not None
                    else None
                ),
                'city_id': (
                    str(record['city']['id']) if record.get('city') else None
                ),
            })
        except ValueError as exc:
            item['motivo'] = str(exc)

    return report


def write_report(path: Path, report: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                'linha',
                'status',
                'motivo',
                'researcher_id',
                'universidade',
                'institution_id',
                'identity_territory',
                'workload',
                'city_id',
            ],
            delimiter=';',
        )
        writer.writeheader()
        writer.writerows(report)


async def process_institution(  # noqa: PLR0913, PLR0917
    session, client, territories, acronym: str, file_path: Path, dry_run: bool
) -> dict:
    print(f'\n==> Processando {acronym} a partir de {file_path.name}...')
    rows = read_institution_rows(file_path, acronym)
    institution_id = await resolve_institution(session, acronym)
    report = await import_rows(
        session,
        rows,
        institution_id,
        CepResolver(client),
        territories,
        dry_run=dry_run,
        acronym=acronym,
    )
    output = report_path(acronym)
    write_report(output, report)
    counts = {
        status: sum(r['status'] == status for r in report)
        for status in ('atualizado', 'simulado', 'ignorado')
    }
    summary = {'acronym': acronym, 'total': len(rows), **counts}
    print(
        f"  Total: {summary['total']} | "
        f"Atualizados: {summary.get('atualizado', 0)} | "
        f"Simulados: {summary.get('simulado', 0)} | "
        f"Ignorados: {summary.get('ignorado', 0)}"
    )
    print(f'  Relatorio: {output}')
    return summary


def resolve_batch_file(path: Path) -> Path | None:
    if path.exists():
        return path
    alt = path.parent / f'_{path.name}'
    return alt if alt.exists() else None


async def main():  # noqa: C901, PLR0912
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--file',
        '-f',
        type=Path,
        default=None,
        help='Caminho do arquivo CSV ou .xlsx.',
    )
    parser.add_argument(
        '--inst',
        default=None,
        type=str.upper,
        choices=INSTITUTION_FORMATS,
        help='Sigla da instituicao (EBMSP, UFOB, UFRB).',
    )
    parser.add_argument(
        '--dry-run', action='store_true', help='Consulta sem gravar no banco.'
    )
    args = parser.parse_args()

    territories = load_territories(DEFAULT_TERRITORIES)
    sys.path.insert(0, str(ROOT / 'src'))
    from simcc.core.settings import Settings  # noqa: PLC0415

    engine = create_async_engine(Settings().DATABASE_URL)
    summaries = []

    try:
        async with (
            async_sessionmaker(engine).begin() as session,
            httpx.AsyncClient(timeout=15) as client,
        ):
            if not await session.scalar(
                text("SELECT to_regclass('public.researcher_institution')")
            ):
                raise ValueError(
                    'Tabela researcher_institution ausente. '
                    'Aplique as migrations.'
                )

            # Modo lote quando nenhum argumento e fornecido
            if not args.file and not args.inst:
                print(
                    '==> Nenhum arquivo/instituicao especificado. '
                    'Executando modo lote completo...'
                )
                for acronym, default_path in DEFAULT_BATCH:
                    target_file = resolve_batch_file(default_path)
                    if not target_file:
                        print(
                            f'Arquivo nao encontrado: {default_path}. Pulando.'
                        )
                        continue
                    s = await process_institution(
                        session,
                        client,
                        territories,
                        acronym,
                        target_file,
                        args.dry_run,
                    )
                    summaries.append(s)
            elif args.file and args.inst:
                s = await process_institution(
                    session,
                    client,
                    territories,
                    args.inst,
                    args.file,
                    args.dry_run,
                )
                summaries.append(s)
            else:
                parser.error(
                    'Informe ambos --file e --inst, ou nenhum para rodar '
                    'em lote com todos.'
                )

        print('\n' + '=' * 50)
        print('RESUMO DA EXECUÇÃO:')
        for s in summaries:
            print(
                f"  [{s['acronym']}] Total: {s['total']} | "
                f"Atualizados: {s.get('atualizado', 0)} | "
                f"Simulados: {s.get('simulado', 0)} | "
                f"Ignorados: {s.get('ignorado', 0)}"
            )
        print('=' * 50)

    finally:
        await engine.dispose()


if __name__ == '__main__':
    loop_factory = (
        asyncio.SelectorEventLoop if sys.platform == 'win32' else None
    )
    asyncio.run(main(), loop_factory=loop_factory)
