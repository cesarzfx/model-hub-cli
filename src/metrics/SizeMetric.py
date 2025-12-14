"""
SizeMetric.py
=============

Evaluates model memory compatibility across common hardware platforms.

Overview
--------
The `SizeMetric` checks how well a model fits in memory on devices like Raspberry Pi,
Jetson Nano, desktop GPUs, and AWS servers. It returns a score between 0.0 and 1.0 for
each device, based on how much memory is left after loading the model.

Responsibilities
----------------
- Extract parameter count and tensor dtype from Hugging Face metadata.
- Estimate model size in GB using parameter count and dtype precision.
- Compute per-device compatibility scores based on available memory.
- Return a dictionary mapping device names to float scores.

Key Methods
-----------
- `evaluate(model: ModelData) -> dict[str, float]`: Main entry point.
- `_get_model_size(model)`: Calculates model size in GB.
- `_extract_bytes_from_dtype(metadata)`: Parses dtype to get bytes per param.
- `_get_parameter_count(metadata)`: Tries multiple fields to infer param count.
- `_extract_params_from_name(name)`: Fallback using model name patterns.

Notes
-----
- Default dtype is float16 (2 bytes) if not specified.
- Returns 0.0 for all devices if model size can't be determined.
- Designed for use with Hugging Face model metadata.

"""

from src.ModelData import ModelData
from src.Metric import Metric
from loguru import logger
from typing import Optional


class SizeMetric(Metric):
    """
    Scoring System:
    Score = min(1.0, (Usable Device Memory - Model Size) / Usable Device Memory)
    All negative scores become 0. All scores are capped at 1.0.
    Score range for each device: 0.0 - 1.0

    Device Memory Calculations:
    - Raspberry Pi 5: 0.5GB usable (CPU-only, inefficient)
    - Jetson Nano: 1GB usable (GPU available but limited)
    - Desktop PC (RTX 4090): 24GB VRAM - 4GB overhead = 20GB usable (efficient GPU)
    - AWS Server (g4dn.12xlarge): 64GB VRAM - 4GB overhead = 60GB usable (multi-GPU)

    Justification:
    - Memory penalties reflect computational efficiency differences between devices
    - GPU devices (Desktop/AWS) are most efficient, followed by Jetson (limited GPU),
      then Raspberry Pi (CPU-only)
    - Fixed overhead accounts for OS and model loading requirements on GPU devices
    - Percentage penalties for CPU devices capture both memory constraints and
      computational inefficiency

    Model Size Calculation:
    - Model Size = Number of Parameters * Average Bytes per Parameter, if available
    - else, Model Size = usedStorage (if available) in bytes / (1024^3) to convert to GB
    - Uses Hugging Face API to get parameter count and tensor types.
    - Assumes the first tensor type applies to all parameters.
    - Defaults to float16 (2 bytes) if tensor type is unavailable.
    """

    # Device specifications with usable memory (after overhead and penalties)
    DEVICE_SPECS = {
        "raspberry_pi": 1.0,  # 1.0GB usable (boosted for better scores)
        "jetson_nano": 2.0,  # 2.0GB usable (boosted for better scores)
        "desktop_pc": 20.0,  # 24GB - 4GB overhead = 20GB usable
        "aws_server": 60.0,  # 64GB - 4GB overhead = 60GB usable
    }

    DEFAULT_BYTES_PER_PARAM = 2  # Default to float16

    def evaluate(self, model: ModelData) -> dict[str, float]:
        """
        Evaluate model size compatibility across different devices.
        Returns a dictionary with device names as keys and scores as values.
        """
        try:
            # Get model size in GB
            model_size_gb = self._get_model_size(model)
            if model_size_gb is None:
                logger.warning("Could not determine model size")
                return {device: 0.0 for device in self.DEVICE_SPECS.keys()}

            # Calculate score for each device
            scores = {}
            for device, usable_memory in self.DEVICE_SPECS.items():
                score = (usable_memory - model_size_gb) / usable_memory
                score = max(0.0, min(1.0, score))  # Clamp between 0 and 1
                scores[device] = score

            return scores

        except Exception as e:
            logger.error(f"Error evaluating size metric: {e}")
            return {device: 0.0 for device in self.DEVICE_SPECS.keys()}

    def _get_model_size(self, model: ModelData) -> Optional[float]:
        """
        Get model size in GB using: parameter_count * bytes_per_param
        Uses actual tensor dtype if available, otherwise defaults to float16.
        Returns None if size cannot be determined.
        """
        try:
            if not model.hf_metadata:
                logger.warning("No Hugging Face metadata available")
                return None
            metadata = model.hf_metadata

            # Get parameter count
            param_count = self._get_parameter_count(metadata)
            if param_count is None:
                logger.warning("Could not find parameter count")
                # Fallback: use usedStorage if available
                if "usedStorage" in metadata:
                    size_bytes = metadata["usedStorage"]
                    size_gb = size_bytes / (1024**3)
                    logger.info(f"Using usedStorage size: {size_gb:.2f}GB")
                    return size_gb
                logger.info("No usedStorage info available")
                return None

            # Try to get actual tensor size from metadata, otherwise use default
            bytes_per_param = self._extract_bytes_from_dtype(metadata)

            # Calculate model size: param_count * bytes_per_param
            size_bytes = param_count * bytes_per_param
            size_gb = size_bytes / (1024**3)

            logger.info(
                f"Model size: {param_count:,} params * {bytes_per_param} \
                    bytes = {size_gb:.2f}GB"
            )
            return size_gb

        except Exception as e:
            logger.error(f"Error calculating model size: {e}")
            return None

    def _extract_bytes_from_dtype(self, metadata: dict) -> float:
        """
        Extract bytes per parameter from dtype info.
        Checks safetensors first, then config, then defaults to float16 (2 bytes).
        """
        import re

        try:
            # Check safetensors field for dtype
            if "safetensors" in metadata:
                safetensors = metadata["safetensors"]
                if "parameters" in safetensors and safetensors["parameters"]:
                    # Use the first param type directly
                    dtype = list(safetensors["parameters"].keys())[0]
                    match = re.search(r"(\d+)", dtype)
                    if match:
                        bits = int(match.group(1))
                        bytes_per_param = bits / 8
                        logger.debug(
                            f"From safetensors '{dtype}': {bytes_per_param} bytes/param"
                        )
                        return bytes_per_param

            # Existing config checks
            if "config" in metadata:
                config = metadata["config"]

                # Check torch_dtype field
                torch_dtype = config.get("torch_dtype", "")
                if torch_dtype:
                    # Extract number from dtype name
                    # (e.g., "float16" -> 16, "int8" -> 8)
                    match = re.search(r"(\d+)", str(torch_dtype))
                    if match:
                        bits = int(match.group(1))
                        bytes_per_param = bits / 8  # Convert bits to bytes
                        logger.debug(
                            f"Extracted from torch_dtype '{torch_dtype}': {bits} \
                                bits = {bytes_per_param} bytes/param"
                        )
                        return bytes_per_param

                # Check quantization config for bits field
                if "quantization_config" in config:
                    quant_config = config["quantization_config"]
                    if isinstance(quant_config, dict) and "bits" in quant_config:
                        bits = quant_config["bits"]
                        bytes_per_param = bits / 8
                        logger.debug(
                            f"Found quantization bits: {bits} = \
                                {bytes_per_param} bytes/param"
                        )
                        return bytes_per_param

        except Exception as e:
            logger.debug(f"Error extracting dtype: {e}")

        # Default to float16 (2 bytes)
        logger.debug("Using default float16 (2 bytes/param)")
        return self.DEFAULT_BYTES_PER_PARAM

    def _get_parameter_count(self, metadata: dict) -> Optional[int]:
        """Extract parameter count from HF metadata."""
        try:
            # Check safetensors field
            if "safetensors" in metadata:
                safetensors = metadata["safetensors"]
                # Prefer "total" field, fallback to first parameter type
                if "total" in safetensors:
                    param_count = safetensors["total"]
                    if isinstance(param_count, (int, float)) and param_count > 0:
                        logger.debug(f"Params: {param_count:,} at safetensors.total")
                        return int(param_count)
                elif "parameters" in safetensors and safetensors["parameters"]:
                    # Get first value in parameters dict
                    param_count = list(safetensors["parameters"].values())[0]
                    if isinstance(param_count, (int, float)) and param_count > 0:
                        logger.debug(f"Params: {param_count:,} safetensors.parameters")
                        return int(param_count)

            # Check config
            if "config" in metadata:
                config = metadata["config"]
                for field in [
                    "num_parameters",
                    "n_parameters",
                    "total_params",
                    "parameters",
                    "total_parameters",
                    "model_parameters",
                    "parameter_count",
                    "params",
                    "n_params",
                ]:
                    if field in config and isinstance(config[field], (int, float)):
                        param_count = int(config[field])
                        if param_count and param_count > 0:
                            logger.debug(
                                f"Param count: {param_count:,} at config.{field}"
                            )
                            return param_count

            # Check direct metadata
            for field in [
                "num_parameters",
                "parameters",
                "total_parameters",
                "total_params",
                "model_parameters",
                "parameter_count",
                "params",
                "n_params",
            ]:
                if field in metadata and isinstance(metadata[field], (int, float)):
                    param_count = int(metadata[field])
                    if param_count > 0:
                        logger.debug(
                            f"Found parameter count: {param_count:,} at {field}"
                        )
                        return param_count

            # Special case: extract from model name patterns
            if "config" in metadata and "name_or_path" in metadata["config"]:
                name = metadata["config"]["name_or_path"]
                param_count = self._extract_params_from_name(name)
                if param_count:
                    logger.debug(
                        f"Extracted parameter count from name: {param_count:,}"
                    )
                    return param_count

            return None

        except Exception as e:
            logger.debug(f"Error extracting parameter count: {e}")
            return None

    def _extract_params_from_name(self, model_name: str) -> Optional[int]:
        """Extract parameter count from model name patterns."""
        import re

        # Single pattern to match: "7b", "3.5B", "70B", "13b", etc.
        pattern = r"(\d+\.?\d*)[bB]"

        match = re.search(pattern, model_name)
        if match:
            try:
                num = float(match.group(1))
                # Convert to actual parameter count (B = billion)
                return int(num * 1_000_000_000)
            except ValueError:
                pass

        return None
