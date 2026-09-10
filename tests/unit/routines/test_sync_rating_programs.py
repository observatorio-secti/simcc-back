# ruff: noqa: PLR2004
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from scripts.routines.sync_admin import sync_rating_programs
from scripts.routines.sync_admin.sync_rating_programs import (
    clean_code,
    get_programs_mapping,
    load_rating_programs_csv,
    main,
    normalize_string,
    process_rating_row,
)


@pytest.mark.unit
def test_clean_code():
    assert clean_code('28001010064P0*') == '28001010064P0'
    assert clean_code('  28001010064P0*  ') == '28001010064P0'
    assert clean_code('28001010064p0') == '28001010064P0'
    assert not clean_code('')
    assert not clean_code(None)


@pytest.mark.unit
def test_normalize_string():
    assert normalize_string('Atenção') == 'atencao'
    assert normalize_string('CÓDIGO\n') == 'codigo'
    assert not normalize_string(None)
    assert normalize_string(123) == '123'
    assert normalize_string('  ESPAÇOS  ') == '  espacos  '


@pytest.mark.unit
def test_process_rating_row_valid():
    programs_map = {'42051010002P0': str(uuid4())}
    row = {'code': '42051010002P0', 'rating': 4}

    data, error = process_rating_row(row, programs_map)
    assert error is None
    assert data == {'code': '42051010002P0', 'rating': '4'}


@pytest.mark.unit
def test_process_rating_row_with_asterisk():
    programs_map = {'28001010064P0': str(uuid4())}
    row = {'code': '28001010064P0*', 'rating': '4'}

    data, error = process_rating_row(row, programs_map)
    assert error is None
    assert data == {'code': '28001010064P0', 'rating': '4'}


@pytest.mark.unit
def test_process_rating_row_missing_code():
    programs_map = {'42051010002P0': str(uuid4())}

    data, error = process_rating_row({'code': '', 'rating': '5'}, programs_map)
    assert data is None
    assert 'Erro: Código do programa vazio ou ausente' in error

    data, error = process_rating_row(
        {'code': None, 'rating': '5'}, programs_map
    )
    assert data is None
    assert 'Erro: Código do programa vazio ou ausente' in error


@pytest.mark.unit
def test_process_rating_row_missing_rating():
    programs_map = {'42051010002P0': str(uuid4())}

    data, error = process_rating_row(
        {'code': '42051010002P0', 'rating': ''}, programs_map
    )
    assert data is None
    assert 'Erro: Nota do programa vazia ou ausente' in error

    data, error = process_rating_row(
        {'code': '42051010002P0', 'rating': None}, programs_map
    )
    assert data is None
    assert 'Erro: Nota do programa vazia ou ausente' in error


@pytest.mark.unit
def test_process_rating_row_program_not_found_in_db():
    programs_map = {'42051010002P0': str(uuid4())}
    row = {'code': '99999999999P9', 'rating': '5'}

    data, error = process_rating_row(row, programs_map)
    assert data is None
    assert 'Ignorado: Programa não cadastrado no banco' in error


@pytest.mark.unit
def test_load_rating_programs_csv(tmp_path):
    csv_file = tmp_path / 'test_ratings.csv'
    csv_file.write_text('Code,Rating\n42051010002P0,5\n32020015008P9,4\n')

    df = load_rating_programs_csv(str(csv_file))
    assert 'code' in df.columns
    assert 'rating' in df.columns
    assert len(df) == 2


@pytest.mark.unit
def test_get_programs_mapping():
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {'code': '42051010002P0', 'graduate_program_id': 'uuid-1'},
        {'code': '32020015008P9', 'graduate_program_id': 'uuid-2'},
    ]
    mock_session.execute.return_value = mock_result

    mapping = get_programs_mapping(mock_session)
    assert mapping == {
        '42051010002P0': 'uuid-1',
        '32020015008P9': 'uuid-2',
    }


@pytest.mark.unit
def test_main_success(tmp_path):
    csv_file = tmp_path / 'rating_programs.csv'
    csv_file.write_text(
        'code,rating\n'
        '42051010002P0,5\n'
        '32020015008P9,4\n'
        '99999999999P9,3\n'  # Ignorado (não no banco)
        ',6\n'  # Erro código
    )

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {'code': '42051010002P0', 'graduate_program_id': 'uuid-1'},
        {'code': '32020015008P9', 'graduate_program_id': 'uuid-2'},
    ]
    mock_session.execute.return_value = mock_result

    main(session=mock_session, csv_path=str(csv_file))

    assert sync_rating_programs.items_found == 4
    assert sync_rating_programs.items_succeeded == 2
    assert sync_rating_programs.items_failed == 2

    # Verifica que session.execute foi chamado com UPDATE
    assert mock_session.execute.call_count == 2  # 1 mapping + 1 update
    update_call_args = mock_session.execute.call_args_list[1]
    update_query = str(update_call_args[0][0])
    update_data = update_call_args[0][1]

    assert 'UPDATE public.graduate_program' in update_query
    assert 'SET rating = :rating' in update_query
    assert 'WHERE code = :code' in update_query
    assert update_data == [
        {'code': '42051010002P0', 'rating': '5'},
        {'code': '32020015008P9', 'rating': '4'},
    ]
    mock_session.commit.assert_called_once()


@pytest.mark.unit
def test_main_missing_required_columns(tmp_path):
    csv_file = tmp_path / 'invalid.csv'
    csv_file.write_text('codigo,nota\n123,4\n')

    mock_session = MagicMock()

    with pytest.raises(ValueError, match='Colunas obrigatórias ausentes'):
        main(session=mock_session, csv_path=str(csv_file))

    assert sync_rating_programs.items_found == 1
    assert sync_rating_programs.items_succeeded == 0
    assert sync_rating_programs.items_failed == 1


@pytest.mark.unit
def test_main_database_error_rollback(tmp_path):
    csv_file = tmp_path / 'rating_programs.csv'
    csv_file.write_text('code,rating\n42051010002P0,5\n')

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {'code': '42051010002P0', 'graduate_program_id': 'uuid-1'}
    ]
    # Falha no execute do UPDATE
    mock_session.execute.side_effect = [
        mock_result,
        RuntimeError('DB Connection Lost'),
    ]

    with pytest.raises(RuntimeError, match='DB Connection Lost'):
        main(session=mock_session, csv_path=str(csv_file))

    mock_session.rollback.assert_called_once()
