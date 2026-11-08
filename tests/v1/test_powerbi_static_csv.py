import csv
import io
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from simcc import app

client = TestClient(app)

ENDPOINTS_AND_COLUMNS = [
    (
        '/researcher_area_leader.csv',
        ['', 'researcher_id', 'area_leader', 'focal_point'],
    ),
    (
        '/guidance.csv',
        [
            '',
            'id',
            'student_lattes_id',
            'supervisor_lattes_id',
            'co_supervisor_lattes_id',
            'graduate_program_id',
            'start_date',
            'planned_date_project',
            'done_date_project',
            'planned_date_qualification',
            'done_date_qualification',
            'planned_date_conclusion',
            'done_date_conclusion',
            'student_name',
            'supervisor_name',
            'co_name',
            'student_researcher_id',
            'supervisor_researcher_id',
            'co_supervisor_researcher_id',
            'program_type',
            'peding_days',
            'peding',
            'type',
            'days_offset',
        ],
    ),
    (
        '/supervisor.csv',
        ['', 'supervisor_researcher_id', 'year', 'count'],
    ),
    (
        '/guidance_per_year.csv',
        [
            '',
            'id',
            'graduate_program_id',
            'student_name',
            'student_researcher_id',
            'supervisor_name',
            'supervisor_researcher_id',
            'co_name',
            'co_supervisor_researcher_id',
            'type',
            'status_',
            'year',
            'in_progress',
        ],
    ),
    (
        '/in_progress_per_year.csv',
        [
            'in_progress',
            'year',
            'supervisor_name',
            'supervisor_researcher_id',
            'graduate_program_id',
            'count',
        ],
    ),
    (
        '/dim_tags.csv',
        ['', 'id', 'name', 'color_code'],
    ),
    (
        '/fat_tags.csv',
        ['', 'guidance_tracking_id', 'tag_id'],
    ),
    (
        '/ind_guidance_ori.csv',
        [
            '',
            'graduate_program_id',
            'year',
            'masters_defenses',
            'doctorate_defenses',
            'permanent_researchers',
            'ind_ori',
        ],
    ),
    (
        '/ind_guidance_distori.csv',
        [
            '',
            'graduate_program_id',
            'year',
            'concluding_researchers',
            'permanent_researchers',
            'ind_dist_ori',
        ],
    ),
    (
        '/ind_guidance_coaut.csv',
        [
            'graduate_program_id',
            'year',
            'IndProdArtCoAut',
            'IndProdLivCoAut',
            'IndProdCapCoAut',
        ],
    ),
    (
        '/fat_guidance_history.csv',
        ['', 'student_name', 'student_id', 'supervisor_id', 'year', 'type'],
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize(
    ('endpoint', 'expected_columns'), ENDPOINTS_AND_COLUMNS
)
def test_powerbi_legacy_csv_endpoints(endpoint, expected_columns):
    # Test root-level route
    response = client.get(endpoint)
    assert response.status_code == HTTPStatus.OK
    assert 'text/csv' in response.headers.get('content-type', '')

    reader = csv.reader(io.StringIO(response.text))
    header = next(reader)
    assert header == expected_columns
    # Ensure there are 0 data rows (empty constant file as requested)
    rows = list(reader)
    assert len(rows) == 0

    # Also test /v1 mount
    v1_response = client.get(f'/v1{endpoint}')
    assert v1_response.status_code == HTTPStatus.OK


if __name__ == '__main__':
    for endpoint, cols in ENDPOINTS_AND_COLUMNS:
        test_powerbi_legacy_csv_endpoints(endpoint, cols)
        print(f'PASS: {endpoint}')
    print('All 11 endpoints verified successfully!')
