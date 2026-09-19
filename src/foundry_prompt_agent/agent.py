import os

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


def ask_agent(query: str) -> tuple[str, dict]:
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

    usage = {
        "model": response.model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.total_tokens,
        "cached_tokens": response.usage.input_tokens_details.cached_tokens,
        "reasoning_tokens": response.usage.output_tokens_details.reasoning_tokens,
    }

    return response.output_text, usage


if __name__ == "__main__":
    answer, usage = ask_agent("Tell me what you can help with.")
    print(answer)
    print(usage)

## run this using following uv command:
# uv run src/foundry_prompt_agent/agent.py 