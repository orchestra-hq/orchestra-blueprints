import json
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool
from orchestra_sdk.orchestra import OrchestraSDK

SET_OUTPUT_TOOL_NAME = "orchestra_set_outputs"
LOCAL_TOOL_SERVER_NAME = "orchestra_local"


def _serialize_output_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if value is None:
        return ""
    return str(value)


def build_orchestra_output_server(
    orchestra: OrchestraSDK, set_output_enabled: bool
) -> Any:
    @tool(
        SET_OUTPUT_TOOL_NAME,
        "Set an output on the current Orchestra Python task.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Output variable name"},
                "value": {
                    "description": "Output value to persist",
                    "oneOf": [
                        {"type": "string"},
                        {"type": "number"},
                        {"type": "boolean"},
                        {"type": "object"},
                        {"type": "array"},
                        {"type": "null"},
                    ],
                },
            },
            "required": ["name", "value"],
        },
    )
    async def orchestra_set_outputs(args: dict[str, Any]) -> dict[str, Any]:
        if not set_output_enabled:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Tool disabled: only available when prompt contains "
                            f"'{SET_OUTPUT_TOOL_NAME}'."
                        ),
                    }
                ],
                "is_error": True,
            }

        name = args.get("name")
        if not isinstance(name, str) or not name.strip():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Invalid 'name': must be a non-empty string.",
                    }
                ],
                "is_error": True,
            }

        value = _serialize_output_value(args.get("value"))
        orchestra.set_output(name=name, value=value)
        return {
            "content": [
                {"type": "text", "text": f"Set Orchestra output '{name}' successfully."}
            ]
        }

    return create_sdk_mcp_server(
        name=LOCAL_TOOL_SERVER_NAME,
        version="1.0.0",
        tools=[orchestra_set_outputs],
    )
