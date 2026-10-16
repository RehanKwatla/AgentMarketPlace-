"""Validation helpers for service metadata and JSON Schemas."""
from typing import Any, Dict
import jsonschema
from backend.shared.errors import AgentEconomyBaseException
from backend.shared.constants import NETWORK_BASE_SEPOLIA, usdc_to_base_units


class RegistryValidationError(AgentEconomyBaseException):
    def __init__(self, message: str):
        super().__init__(message, error_code="VALIDATION_ERROR")


ValidationError = RegistryValidationError



def validate_json_schema(schema: Dict[str, Any], field_name: str = "schema") -> None:
    """Validate that a dictionary is a syntactically valid JSON Schema (Draft 7)."""
    if not isinstance(schema, dict):
        raise ValidationError(
            f"The '{field_name}' must be a JSON object, got {type(schema).__name__}."
        )

    # Allow empty schema if intentionally unconstrained
    if not schema:
        return

    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.SchemaError as e:
        raise ValidationError(f"Invalid JSON Schema for '{field_name}': {e.message}")


def validate_service_registration(data: Dict[str, Any]) -> None:
    """Validate full service definition fields against contract requirements."""
    required_fields = [
        "service_id",
        "name",
        "category",
        "endpoint_url",
        "price_usdc",
        "network",
        "pay_to",
        "input_schema",
        "output_schema",
    ]
    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required service metadata field: '{field}'")
        if isinstance(data[field], str) and not data[field].strip():
            raise ValidationError(f"Field '{field}' cannot be empty.")

    # Validate Network: Must be Base Sepolia
    network = data.get("network")
    if network != NETWORK_BASE_SEPOLIA:
        raise ValidationError(
            f"Unsupported network '{network}'. Only Base Sepolia ('{NETWORK_BASE_SEPOLIA}') is permitted."
        )

    # Validate price is strictly positive
    price_usdc = str(data.get("price_usdc", "0"))
    try:
        atomic = usdc_to_base_units(price_usdc)
        if atomic <= 0:
            raise ValidationError("Service price must be strictly positive (> 0).")
    except Exception as e:
        raise ValidationError(f"Invalid USDC price formatting '{price_usdc}': {e}")

    # Validate recipient address
    pay_to = str(data.get("pay_to", ""))
    if not pay_to.startswith("0x") or len(pay_to) < 42:
        raise ValidationError(f"Invalid seller pay_to address: '{pay_to}'")

    # Validate JSON schemas
    validate_json_schema(data.get("input_schema", {}), "input_schema")
    validate_json_schema(data.get("output_schema", {}), "output_schema")
