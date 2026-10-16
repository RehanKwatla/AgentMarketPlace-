"""Validation logic for Service Registry records and capability schemas."""
import re
from typing import Any, Dict
import jsonschema
from backend.shared.constants import NETWORK_BASE_SEPOLIA
from backend.shared.errors import AgentEconomyBaseException


class ServiceValidationError(AgentEconomyBaseException):
    def __init__(self, message: str):
        super().__init__(message, error_code="VALIDATION_ERROR")


def validate_json_schema(schema: Dict[str, Any], schema_name: str = "schema") -> None:
    """Validate that a dictionary is a syntactically valid JSON Schema."""
    if not isinstance(schema, dict):
        raise ServiceValidationError(f"{schema_name} must be a dictionary object.")
    try:
        # Check against Draft-7 or Draft-2020-12 meta-schema
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.exceptions.SchemaError as e:
        raise ServiceValidationError(f"Invalid {schema_name}: {e.message}")


def validate_service_registration(data: Dict[str, Any]) -> None:
    """Comprehensive validation for incoming service registrations."""
    # 1. Service ID
    service_id = data.get("service_id", "")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", service_id):
        raise ServiceValidationError(
            f"service_id '{service_id}' contains invalid characters. Use alphanumeric, dashes, or underscores."
        )

    # 2. Network Check
    network = data.get("network", "")
    if network.lower() != NETWORK_BASE_SEPOLIA.lower():
        raise ServiceValidationError(
            f"Network '{network}' is not allowed. Only '{NETWORK_BASE_SEPOLIA}' is supported."
        )

    # 3. PayTo Address Check
    pay_to = data.get("pay_to", "")
    if not re.match(r"^0x[a-fA-F0-9]{40}$", pay_to):
        raise ServiceValidationError(
            f"pay_to address '{pay_to}' is not a valid 20-byte Ethereum/Base address."
        )

    # 4. Endpoint URL Check
    endpoint_url = data.get("endpoint_url", "")
    if not (endpoint_url.startswith("http://") or endpoint_url.startswith("https://")):
        raise ServiceValidationError(
            f"endpoint_url '{endpoint_url}' must start with http:// or https://"
        )

    # 5. Price Check
    price_atomic = data.get("price_atomic", 0)
    if price_atomic < 0:
        raise ServiceValidationError("Service price cannot be negative.")

    # 6. Schemas
    validate_json_schema(data.get("input_schema", {}), "input_schema")
    validate_json_schema(data.get("output_schema", {}), "output_schema")
