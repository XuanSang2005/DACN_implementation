"""Small synthetic data; no business dataset copied into tests."""

import pytest

from dacn_s01.repository import Repository
from dacn_s01.service import Service


@pytest.fixture
def payload():
    return {
        'schema_version': '1.0.0', 'title': 'Synthetic', 'context': 'Unknown business scope',
        'actors': ['A', 'B'],
        'functional_requirements': [{'id': 'R1', 'text': '  Preserve text  ', 'priority': None,
                                     'acceptance_criteria': ['Second', 'First', 'First']}],
        'non_functional_requirements': [],
        'constraints': [{'id': 'C1', 'text': 'Local constraint', 'priority': 'must',
                         'acceptance_criteria': [], 'constraint': {'kind': 'local', 'value': None}}],
        'design_preferences': {'metric_priorities': ['response_time_p95', 'sustainable_throughput',
                                                    'cpu_utilisation', 'scaling_gain']},
        'operating_conditions': dict.fromkeys(['critical_scenarios', 'expected_load', 'peak_load',
                                             'data_volume', 'growth', 'resource_budget'], None),
    }


@pytest.fixture
def repository(tmp_path):
    repository = Repository(tmp_path / 'state.sqlite3')
    repository.initialize()
    return repository


@pytest.fixture
def service(repository):
    return Service(repository)
