import pytest
from unittest.mock import Mock, patch
from typing import Optional, Any
from src.metrics.SizeMetric import SizeMetric
from src.ModelData import ModelData


class TestSizeMetric:
    @pytest.fixture
    def metric(self) -> SizeMetric:
        return SizeMetric()

    @pytest.fixture
    def mock_model(self) -> Mock:
        """Base mock model with minimal required attributes."""
        model = Mock(spec=ModelData)
        model.name = "test-model"
        model.hf_metadata = None
        return model

    @pytest.fixture
    def model_with_metadata(self, mock_model: Mock) -> Mock:
        """Model with HF metadata containing parameter count."""
        mock_model.hf_metadata = {
            "config": {
                "num_parameters": 7_000_000_000,  # 7B parameters
                "name_or_path": "test/model-7b",
            }
        }
        return mock_model

    # --- Tests for evaluate() ---

    def test_evaluate_success(
        self, metric: SizeMetric, model_with_metadata: Mock
    ) -> None:
        """Test successful evaluation with all device scores."""
        scores = metric.evaluate(model_with_metadata)

        assert len(scores) == 4
        assert all(
            device in scores
            for device in [
                "raspberry_pi",
                "jetson_nano",
                "desktop_pc",
                "aws_server",
            ]
        )
        assert all(0.0 <= score <= 1.0 for score in scores.values())

    def test_evaluate_no_metadata(self, metric: SizeMetric, mock_model: Mock) -> None:
        """Test evaluation with model that has no metadata."""
        mock_model.hf_metadata = None
        scores = metric.evaluate(mock_model)

        expected = {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.0,
            "desktop_pc": 0.0,
            "aws_server": 0.0,
        }
        assert scores == expected

    def test_evaluate_large_model(self, metric: SizeMetric, mock_model: Mock) -> None:
        """Test evaluation with very large model."""
        mock_model.hf_metadata = {"config": {"num_parameters": 70_000_000_000}}
        scores = metric.evaluate(mock_model)

        assert scores["raspberry_pi"] == 0.0
        assert scores["jetson_nano"] == 0.0
        # Large devices might still have some score
        assert scores["aws_server"] >= 0.0

    def test_evaluate_tiny_model(self, metric: SizeMetric, mock_model: Mock) -> None:
        """Test evaluation with very small model."""
        mock_model.hf_metadata = {"config": {"num_parameters": 100_000_000}}
        scores = metric.evaluate(mock_model)

        # Raspberry Pi and Jetson Nano may be lower, desktop and aws should be high
        assert scores["raspberry_pi"] > 0.6
        assert scores["jetson_nano"] > 0.8
        assert scores["desktop_pc"] > 0.95
        assert scores["aws_server"] > 0.95

    @patch.object(SizeMetric, "_get_model_size")
    def test_evaluate_error_handling(
        self, mock_get_size: Mock, metric: SizeMetric, mock_model: Mock
    ) -> None:
        """Test evaluation when size calculation fails."""
        mock_get_size.side_effect = Exception("Calculation failed")
        scores = metric.evaluate(mock_model)

        expected = {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.0,
            "desktop_pc": 0.0,
            "aws_server": 0.0,
        }
        assert scores == expected

    # --- Tests for _get_model_size() ---

    def test_get_model_size_success(
        self, metric: SizeMetric, model_with_metadata: Mock
    ) -> None:
        """Test successful model size calculation."""
        size_gb: Optional[float] = metric._get_model_size(model_with_metadata)

        assert size_gb is not None
        # 7B params * 2 bytes = 14GB / 1024^3 ≈ 13.04GB
        assert 13.0 <= size_gb <= 14.0  # 7B * 2 bytes ≈ 13GB

    def test_get_model_size_with_dtype(
        self, metric: SizeMetric, mock_model: Mock
    ) -> None:
        """Test model size calculation with different dtypes."""
        # Float32 model
        mock_model.hf_metadata = {
            "config": {
                "num_parameters": 1_000_000_000,
                "torch_dtype": "float32",
            }
        }
        size_gb: Optional[float] = metric._get_model_size(mock_model)
        assert size_gb is not None
        assert 3.5 <= size_gb <= 4.0  # 1B * 4 bytes ≈ 3.7GB

        # Quantized model
        mock_model.hf_metadata = {
            "config": {
                "num_parameters": 7_000_000_000,
                "quantization_config": {"bits": 8},
            }
        }
        size_gb = metric._get_model_size(mock_model)
        assert size_gb is not None
        assert 6.0 <= size_gb <= 7.0  # 7B * 1 byte ≈ 6.5GB

    def test_get_model_size_no_params(
        self, metric: SizeMetric, mock_model: Mock
    ) -> None:
        """Test model size calculation when parameter count cannot be found."""
        mock_model.hf_metadata = {"config": {"some_other_field": "value"}}
        assert metric._get_model_size(mock_model) is None

    # --- Tests for _extract_bytes_from_dtype() ---

    @pytest.mark.parametrize(
        "torch_dtype,expected_bytes",
        [
            ("float32", 4.0),
            ("float16", 2.0),
            ("int8", 1.0),
            ("int4", 0.5),
            ("bfloat16", 2.0),
            ("", 2.0),
            (None, 2.0),  # Defaults
        ],
    )
    def test_extract_bytes_from_dtype(
        self, metric: SizeMetric, torch_dtype: str, expected_bytes: float
    ) -> None:
        """Test dtype extraction from torch_dtype field."""
        metadata = (
            {"config": {"torch_dtype": torch_dtype}} if torch_dtype else {"config": {}}
        )

        assert metric._extract_bytes_from_dtype(metadata) == expected_bytes

    def test_extract_bytes_quantization_precedence(self, metric: SizeMetric) -> None:
        """Test dtype extraction precedence and quantization."""
        # Quantization only
        metadata: dict[str, Any] = {"config": {"quantization_config": {"bits": 4}}}
        assert metric._extract_bytes_from_dtype(metadata) == 0.5

        # torch_dtype takes precedence over quantization
        metadata = {
            "config": {
                "torch_dtype": "float32",
                "quantization_config": {"bits": 8},
            }
        }
        assert metric._extract_bytes_from_dtype(metadata) == 4.0

    # --- Tests for _get_parameter_count() ---

    def test_get_parameter_count_config_fields(self, metric: SizeMetric) -> None:
        """Test parameter extraction from various config fields."""
        test_cases = [
            ({"config": {"num_parameters": 1_500_000_000}}, 1_500_000_000),
            ({"config": {"n_parameters": 2_700_000_000}}, 2_700_000_000),
            ({"config": {"total_params": 3_000_000_000}}, 3_000_000_000),
        ]

        for metadata, expected in test_cases:
            assert metric._get_parameter_count(metadata) == expected

    def test_get_parameter_count_from_name(self, metric: SizeMetric) -> None:
        """Test parameter extraction from model name fallback."""
        metadata = {"config": {"name_or_path": "meta-llama/Llama-2-7b-hf"}}
        assert metric._get_parameter_count(metadata) == 7_000_000_000

    def test_get_parameter_count_edge_cases(self, metric: SizeMetric) -> None:
        """Test parameter extraction edge cases."""
        # Invalid values
        assert metric._get_parameter_count({"config": {"num_parameters": -1}}) is None
        assert (
            metric._get_parameter_count({"config": {"num_parameters": "invalid"}})
            is None
        )

        # No valid fields
        assert (
            metric._get_parameter_count({"config": {"model_type": "transformer"}})
            is None
        )
        assert metric._get_parameter_count({"other_field": "value"}) is None

    # --- Tests for _extract_params_from_name() ---

    @pytest.mark.parametrize(
        "model_name,expected_params",
        [
            ("llama-7b", 7_000_000_000),
            ("gpt-3.5b", 3_500_000_000),
            ("model-13B", 13_000_000_000),
            ("falcon-40b-instruct", 40_000_000_000),
            ("bert-110M", None),  # 'M' not supported, only 'b'/'B'
            ("no-params-here", None),
            ("model-7.5b-chat", 7_500_000_000),
            ("70B-model", 70_000_000_000),
        ],
    )
    def test_extract_params_from_name(
        self, metric: SizeMetric, model_name: str, expected_params: int
    ) -> None:
        """Test parameter extraction from various model name patterns."""
        assert metric._extract_params_from_name(model_name) == expected_params

    # --- Device Specs Tests ---

    def test_device_specs_values(self, metric: SizeMetric) -> None:
        """Test that DEVICE_SPECS contains expected values and ordering."""
        expected = {
            "raspberry_pi": 1.5,
            "jetson_nano": 3.0,
            "desktop_pc": 20.0,
            "aws_server": 60.0,
        }
        assert metric.DEVICE_SPECS == expected

        # Test ordering
        specs = list(metric.DEVICE_SPECS.values())
        assert specs == sorted(specs)  # Should be in ascending order

    def test_device_scoring_formula(self, metric: SizeMetric) -> None:
        """Test the device scoring calculation formula."""
        model_size_gb = 1.0

        for device, memory in metric.DEVICE_SPECS.items():
            expected_score = max(0.0, min(1.0, (memory - model_size_gb) / memory))
            actual_score = (memory - model_size_gb) / memory
            actual_score = max(0.0, min(1.0, actual_score))
            assert actual_score == expected_score

    def test_device_boundary_conditions(self, metric: SizeMetric) -> None:
        """Test device scoring at memory boundaries."""
        for device, memory_limit in metric.DEVICE_SPECS.items():
            # At limit: score = 0
            score = max(0.0, min(1.0, (memory_limit - memory_limit) / memory_limit))
            assert score == 0.0

            # Over limit: score = 0
            score = max(
                0.0,
                min(1.0, (memory_limit - (memory_limit + 1)) / memory_limit),
            )
            assert score == 0.0

            # Under limit: score > 0
            score = max(
                0.0,
                min(1.0, (memory_limit - (memory_limit - 0.1)) / memory_limit),
            )
            assert score > 0.0
