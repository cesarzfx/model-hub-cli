import pytest

from src.metrics.AvailabilityMetric import AvailabilityMetric
from tests.conftest import StubModelData


@pytest.mark.parametrize(
    "code_link, dataset_link, github_meta, dataset_meta, hf_meta, expected_score",
    [
        # All available: HF (1) + GitHub (1) + Dataset (1) = 3/3 = 1.0
        (
            "https://github.com/org/repo",
            "https://huggingface.co/datasets/org/data",
            {"stars": 123},
            {"name": "dataset"},
            {"downloads": 100},
            1.0,
        ),
        # HF (1) + GitHub (1) + Dataset missing (0) = 2/3 = 0.67
        (
            "https://github.com/org/repo",
            "https://huggingface.co/datasets/org/data",
            {"stars": 999},
            {},
            {"downloads": 100},
            0.67,
        ),
        # HF (1) + GitHub missing (0) + Dataset (1) = 2/3 = 0.67
        (
            "https://github.com/org/repo",
            "https://huggingface.co/datasets/org/data",
            {},
            {"name": "dataset"},
            {"downloads": 100},
            0.67,
        ),
        # HF (1) + GitHub missing (0) + Dataset missing (0) = 1/3 = 0.33
        (
            "https://github.com/org/repo",
            "https://huggingface.co/datasets/org/data",
            {},
            {},
            {"downloads": 100},
            0.33,
        ),
        # HF (1) + GitHub (1), no dataset link = 2/2 = 1.0
        (
            "https://github.com/org/repo",
            None,
            {"stars": 42},
            {},
            {"downloads": 100},
            1.0,
        ),
        # HF (1) + Dataset (1), no code link = 2/2 = 1.0
        (
            None,
            "https://huggingface.co/datasets/org/data",
            {},
            {"name": "dataset"},
            {"downloads": 100},
            1.0,
        ),
        # No HF metadata = 0/1 = 0.0
        (
            None,
            None,
            {},
            {},
            {},
            0.0,
        ),
    ],
)
def test_availability_metric_scores(
    code_link,
    dataset_link,
    github_meta,
    dataset_meta,
    hf_meta,
    expected_score,
):
    model = StubModelData(
        modelLink="https://huggingface.co/org/model",
        codeLink=code_link,
        datasetLink=dataset_link,
    )
    model.github_metadata = github_meta
    model.dataset_metadata = dataset_meta
    model.hf_metadata = hf_meta
    score = AvailabilityMetric().evaluate(model)
    assert pytest.approx(score, 0.01) == expected_score


def test_availability_metric_none_metadata():
    model = StubModelData(
        modelLink="https://huggingface.co/org/model",
        codeLink="https://github.com/org/repo",
        datasetLink="https://huggingface.co/datasets/org/data",
    )
    model.github_metadata = None
    model.dataset_metadata = None
    model.hf_metadata = {}
    score = AvailabilityMetric().evaluate(model)
    assert score == 0.0
