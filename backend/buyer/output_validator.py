"""Output Validator ensuring seller payloads strictly conform to registered JSON schemas."""
from typing import Any, Dict, Tuple
import jsonschema


class OutputValidator:
    """Validates raw service responses against registered service output schemas."""

    def validate_output(
        self,
        output_payload: Any,
        output_schema: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate payload against schema.
        Returns:
            (is_valid: bool, error_message: str)
        """
        if not output_schema:
            # If no schema defined, consider accepted
            return True, ""

        if not isinstance(output_payload, dict):
            return False, f"Expected dictionary payload, got {type(output_payload).__name__}"

        try:
            validator = jsonschema.Draft7Validator(output_schema)
            errors = list(validator.iter_errors(output_payload))
            if errors:
                err_msgs = [e.message for e in errors]
                return False, f"Schema validation failed: {'; '.join(err_msgs)}"
            return True, ""
        except Exception as e:
            return False, f"Validation engine error: {str(e)}"

    @classmethod
    def validate_seller_output(cls, output_payload: Any, output_schema: Dict[str, Any]) -> bool:
        """Convenience method returning bool for quick validation checks."""
        valid, _ = cls().validate_output(output_payload, output_schema)
        return valid

