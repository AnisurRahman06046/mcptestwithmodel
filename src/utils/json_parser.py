"""
JSON Parser Utility for LLM Responses
Handles messy LLM output with mixed JSON and text
"""

import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def safe_parse_llm_json(response_text: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract and safely parse a JSON object from LLM response text.

    Handles:
    - Extra commentary before/after JSON
    - Trailing commas
    - Single quotes (converts to double quotes)
    - Multiple JSON blocks (returns first valid one)
    - Malformed JSON with recovery attempt

    Args:
        response_text: Raw LLM response that may contain JSON
        fallback: Custom fallback dict if parsing fails

    Returns:
        Parsed JSON as dict, or fallback if parsing fails
    """

    # Default fallback for query processing
    if fallback is None:
        fallback = {
            "intent": "general",
            "confidence": 0.5,
            "tools": [],
            "reasoning": "Failed to parse LLM response"
        }

    if not response_text:
        logger.warning("Empty response text provided")
        return fallback

    # Check for JSON wrapped in tags first
    if "<json>" in response_text and "</json>" in response_text:
        start_tag = response_text.find("<json>") + 6
        end_tag = response_text.find("</json>")
        if start_tag < end_tag:
            try:
                json_str = response_text[start_tag:end_tag].strip()
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    return ensure_tool_response_defaults(parsed)
            except json.JSONDecodeError:
                logger.debug("Failed to parse JSON from tags, trying other methods")

    try:
        # Try parsing the entire response as JSON (fastest path)
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass  # Continue with extraction methods

    try:
        # Method 1: Find JSON block by counting braces
        json_start = response_text.find("{")
        if json_start == -1:
            logger.warning("No JSON object found in LLM response")
            return fallback

        brace_count = 0
        json_end = None

        for i, ch in enumerate(response_text[json_start:], start=json_start):
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end is None:
            logger.error("Could not find matching closing brace in LLM response")
            return fallback

        json_str = response_text[json_start:json_end]

        # Clean common JSON issues
        json_str = clean_json_string(json_str)

        # Try to parse cleaned JSON
        parsed = json.loads(json_str)

        # Validate and add defaults for tool selection responses
        if isinstance(parsed, dict):
            parsed = ensure_tool_response_defaults(parsed)

        return parsed

    except json.JSONDecodeError as e:
        # Method 2: Try regex extraction as last resort
        logger.debug(f"Brace counting failed: {e}, trying regex extraction")

        try:
            # Look for JSON-like structure with regex
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)

            for match in matches:
                try:
                    cleaned = clean_json_string(match)
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict):
                        return ensure_tool_response_defaults(parsed)
                except:
                    continue

        except Exception as regex_error:
            logger.debug(f"Regex extraction failed: {regex_error}")

    except Exception as e:
        logger.error(f"Unexpected error parsing LLM JSON: {e}")

    logger.error(f"All parsing methods failed. Response preview: {response_text[:200]}...")
    return fallback


def clean_json_string(json_str: str) -> str:
    """
    Clean common JSON formatting issues from LLM output

    Args:
        json_str: Raw JSON string that may have issues

    Returns:
        Cleaned JSON string
    """
    # Replace single quotes with double quotes (careful with apostrophes in values)
    # This regex only replaces single quotes used for JSON keys/values, not apostrophes
    json_str = re.sub(r"(?<![a-zA-Z])'([^']*)'(?![a-zA-Z])", r'"\1"', json_str)

    # Remove trailing commas before closing braces/brackets
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # Remove newlines that might break JSON parsing
    json_str = json_str.replace('\n}', '}')
    json_str = json_str.replace(',\n}', '}')

    # Fix common quote escaping issues
    json_str = json_str.replace('\\"', '"')
    json_str = json_str.replace("\\'", "'")

    return json_str


def ensure_tool_response_defaults(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure tool response has required fields with defaults

    Args:
        parsed: Parsed JSON dictionary

    Returns:
        Dictionary with required fields guaranteed
    """
    # Add defaults for missing fields
    parsed.setdefault("intent", "general")
    parsed.setdefault("confidence", 0.7)
    parsed.setdefault("tools", [])

    # Ensure confidence is a float between 0 and 1
    if "confidence" in parsed:
        try:
            confidence = float(parsed["confidence"])
            parsed["confidence"] = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            parsed["confidence"] = 0.7

    # Ensure tools is a list
    if not isinstance(parsed.get("tools"), list):
        parsed["tools"] = []

    # Validate each tool has required fields
    for tool in parsed["tools"]:
        if isinstance(tool, dict):
            tool.setdefault("name", "unknown")
            tool.setdefault("parameters", {})

    return parsed


def extract_json_blocks(response_text: str) -> list:
    """
    Extract all JSON blocks from text (useful for multiple tool calls)

    Args:
        response_text: Text that may contain multiple JSON blocks

    Returns:
        List of parsed JSON objects
    """
    json_blocks = []

    # Find all potential JSON blocks
    current_pos = 0
    while True:
        json_start = response_text.find("{", current_pos)
        if json_start == -1:
            break

        brace_count = 0
        json_end = None

        for i, ch in enumerate(response_text[json_start:], start=json_start):
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break

        if json_end:
            json_str = response_text[json_start:json_end]
            try:
                cleaned = clean_json_string(json_str)
                parsed = json.loads(cleaned)
                json_blocks.append(parsed)
            except:
                pass  # Skip invalid JSON blocks

            current_pos = json_end
        else:
            break

    return json_blocks