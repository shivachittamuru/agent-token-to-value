import os
import time

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


project_client = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    # az.cmd can cold-start slower than the 10s default on Windows.
    credential=AzureCliCredential(process_timeout=30),
)

openai_client = project_client.get_openai_client()

AGENT_NAME = os.environ["FOUNDRY_AGENT_NAME"]
AGENT_VERSION = os.environ["FOUNDRY_AGENT_VERSION"]


def extract_tool_calls(response) -> tuple[int | None, list[str] | None]:
    """Capture server-side tool calls exposed on the Responses output.

    The live Responses object lists tool calls as output items whose ``type``
    ends with ``_call`` (for example ``azure_ai_search_call``), while their
    results end with ``_call_output``. When ``output`` is not a readable list
    we cannot observe tool usage, so we return Unknown (None) rather than
    inferring zero from the agent configuration or prompt.
    """

    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return None, None

    tool_types = [
        item_type
        for item in output
        if (item_type := getattr(item, "type", None))
        and item_type.endswith("_call")
    ]

    return len(tool_types), sorted(set(tool_types))


def ask_agent(query: str) -> tuple[str, dict]:
    start = time.perf_counter()
    response = openai_client.responses.create(
        input=[{"role": "user", "content": query}],
        extra_body={
            "agent_reference": {
                "name": AGENT_NAME,
                "version": AGENT_VERSION,
                "type": "agent_reference",
            }
        },
    )
    latency_ms = (time.perf_counter() - start) * 1000

    tool_call_count, tool_types = extract_tool_calls(response)

    execution = {
        "response_id": getattr(response, "id", None),
        "agent_name": AGENT_NAME,
        "agent_version": AGENT_VERSION,
        "model": response.model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cached_tokens": response.usage.input_tokens_details.cached_tokens,
        "reasoning_tokens": response.usage.output_tokens_details.reasoning_tokens,
        "total_tokens": response.usage.total_tokens,
        "latency_ms": latency_ms,
        "tool_call_count": tool_call_count,
        "tool_types": tool_types,
    }

    return response.output_text, execution


if __name__ == "__main__":
    answer, execution = ask_agent("Tell me what you can help with.")
    print(answer)
    print(execution)

## run this using following uv command:
# uv run src/foundry_prompt_agent/agent.py 