"""Output Validator ensuring seller payloads strictly conform to registered JSON schemas."""
import json
from typing import Any, Dict, Optional, Tuple
import jsonschema


class OutputValidator:
    """Validates raw service responses against registered service output schemas."""

    def validate_output(
        self,
        output_payload: Any,
        output_schema: Dict[str, Any],
        content_type: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Validate payload against schema.

        Rejects:
        - Invalid content types (e.g. text/html, text/plain)
        - Malformed JSON strings
        - Non-dictionary response structures
        - Missing required fields
        - Field type mismatches
        - Unexpected additional properties (when restricted)

        Returns:
            (is_valid: bool, error_message: str)
        """
        # 1. Content-Type verification
        if content_type:
            cleaned_ct = content_type.split(";")[0].strip().lower()
            if cleaned_ct not in ["application/json", "text/json", "application/problem+json"]:
                return False, f"Invalid Content-Type: '{content_type}'. Expected 'application/json'."

        # 2. Parse string payload if raw JSON string was passed
        payload_obj = output_payload
        if isinstance(output_payload, (str, bytes)):
            try:
                payload_obj = json.loads(output_payload)
            except Exception as e:
                return False, f"Malformed JSON: unable to parse response body as valid JSON: {str(e)}"

        # 3. Structure check
        if not isinstance(payload_obj, dict):
            return False, f"Unexpected response structure: expected JSON object (dict), received {type(payload_obj).__name__}"

        if not output_schema:
            return True, ""

        # 4. Draft-7 Schema Validation
        try:
            validator = jsonschema.Draft7Validator(output_schema)
            errors = list(validator.iter_errors(payload_obj))
            if errors:
                formatted_errors = []
                for e in errors:
                    path = ".".join(str(p) for p in e.path) if e.path else "root"
                    if e.validator == "required":
                        formatted_errors.append(f"Missing required field(s): {e.message}")
                    elif e.validator == "type":
                        formatted_errors.append(f"Type mismatch at '{path}': {e.message}")
                    elif e.validator == "additionalProperties":
                        formatted_errors.append(f"Unexpected additional field at '{path}': {e.message}")
                    else:
                        formatted_errors.append(f"Validation error at '{path}': {e.message}")
                return False, f"Schema validation failed: {'; '.join(formatted_errors)}"
            return True, ""
        except jsonschema.SchemaError as se:
            return False, f"Invalid registered output schema: {se.message}"
        except Exception as e:
            return False, f"Validation engine error: {str(e)}"

    def parse_and_validate(
        self,
        raw_content: Any,
        content_type: Optional[str],
        output_schema: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Parse raw HTTP response and validate against schema.

        Returns:
            (is_valid, parsed_dict_or_none, error_msg)
        """
        is_valid, err = self.validate_output(raw_content, output_schema, content_type=content_type)
        if not is_valid:
            parsed = None
            if isinstance(raw_content, dict):
                parsed = raw_content
            else:
                try:
                    parsed = json.loads(raw_content)
                except Exception:
                    parsed = None
            return False, parsed, err

        if isinstance(raw_content, dict):
            return True, raw_content, ""
        try:
            return True, json.loads(raw_content), ""
        except Exception as e:
            return False, None, f"Malformed JSON: {str(e)}"

    @classmethod
    def validate_seller_output(cls, output_payload: Any, output_schema: Dict[str, Any]) -> bool:
        """Convenience method returning bool for quick validation checks."""
        valid, _ = cls().validate_output(output_payload, output_schema)
        return valid
