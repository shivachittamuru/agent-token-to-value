---
title: Create the Contoso Coffee Prompt Agent
description: Setup guide for the Foundry Prompt Agent and Azure AI Search connection.
---

## Create the Contoso Coffee Prompt Agent in Foundry

> Implementation reference. See the [README](../README.md) and
> [architecture overview](architecture.md) for the current framework.

This repository assumes a Prompt Agent already exists in your Microsoft Foundry project, backed by an Azure AI Search index built from the Contoso Coffee menu. Nothing in this repo creates that agent, because the agent's instructions, model, and tools are owned by Foundry rather than by source control.

Follow this guide once, before running anything else in the repo. At the end you will have:

- an Azure AI Search index named `contoso-coffee-index` populated from [data/contoso.json](../data/contoso.json)
- a Prompt Agent in Foundry that uses that index as a tool
- a populated `.env` so [src/foundry_prompt_agent/agent.py](../src/foundry_prompt_agent/agent.py) can invoke the agent

## Prerequisites

- An Azure subscription with permission to create resources.
- A Microsoft Foundry project. Note its project endpoint, which becomes `FOUNDRY_PROJECT_ENDPOINT`.
- A deployed chat model in that project, for example `gpt-5`. The same deployment name is reused as the judge model in `FOUNDRY_JUDGE_MODEL`.
- An Azure AI Search service. The Basic tier is sufficient for this menu.
- An Azure Storage account, used to stage the menu file for indexing.
- Azure CLI installed and signed in with `az login`, since the client authenticates using `AzureCliCredential`.

## Step 1: Understand the source data

[data/contoso.json](../data/contoso.json) is a single JSON array of menu items:

```json
[
  {
    "id": "c001",
    "item": "Espresso",
    "price": 2.5,
    "description": "Rich, full-bodied coffee, with a compact crema and strong aroma.",
    "category": "Coffees"
  }
]
```

Two properties of this file matter for indexing. It is a JSON array rather than newline-delimited JSON, so the indexer must use JSON array parsing mode. Also, `id` is unique per item, which makes it a natural key field.

## Step 2: Stage the menu file in Blob Storage

The Azure AI Search import wizard reads from a data source rather than from your local disk, so upload the file first.

1. Open your storage account in the Azure portal.
2. Create a container named `contoso-menu`.
3. Upload [data/contoso.json](../data/contoso.json) into that container.

You can do the same from the CLI:

```bash
az storage blob upload \
  --account-name <your-storage-account> \
  --container-name contoso-menu \
  --name contoso.json \
  --file data/contoso.json \
  --auth-mode login
```

## Step 3: Create the `contoso-coffee-index`

1. Open your Azure AI Search service in the Azure portal.
2. Select **Import data**.
3. For the data source, choose **Azure Blob Storage** and point it at the `contoso-menu` container.
4. Set **Parsing mode** to **JSON array**. This is the step most people miss. Without it, the whole file is indexed as one document instead of one document per menu item.
5. Skip cognitive skills. The menu is already structured, so enrichment adds nothing here.
6. Name the index `contoso-coffee-index` and configure the fields as shown below.
7. Name the indexer, then run it.

Field configuration:

| Field         | Type          | Key | Retrievable | Searchable | Filterable | Sortable | Facetable |
|---------------|---------------|-----|-------------|------------|------------|----------|-----------|
| `id`          | `Edm.String`  | Yes | Yes         | No         | Yes        | No       | No        |
| `item`        | `Edm.String`  | No  | Yes         | Yes        | Yes        | Yes      | No        |
| `price`       | `Edm.Double`  | No  | Yes         | No         | Yes        | Yes      | No        |
| `description` | `Edm.String`  | No  | Yes         | Yes        | No         | No       | No        |
| `category`    | `Edm.String`  | No  | Yes         | Yes        | Yes        | Yes      | Yes       |

`price` must be `Edm.Double` rather than a string, otherwise budget questions such as "what can I get under $3" cannot be filtered or sorted correctly.

After the indexer runs, open **Search explorer** and confirm the document count matches the number of items in the menu file. A count of `1` means the parsing mode was left at its default.

## Step 4: Connect Azure AI Search to your Foundry project

1. Open your project in the Foundry portal.
2. Go to **Management center**, then **Connected resources**.
3. Add a new connection of type **Azure AI Search** and select the search service from Step 3.

The agent tool in the next step selects this connection, so the connection must exist first.

## Step 5: Create the Prompt Agent

1. In the Foundry portal, open **Agents** and create a new Prompt Agent.
2. Name it `foundry-prompt-agent`, matching `FOUNDRY_AGENT_NAME` in [.env.example](../.env.example).
3. Select your deployed chat model, for example `gpt-5`.
4. Paste the instructions below into the agent's instructions field.

```text
You are a helpful assistant for the Contoso Coffee shop. Only answer user questions related to the shop and nothing else.

Use the connected Azure AI Search tool to answer questions about the menu,
including items, prices, descriptions, and categories.

Always search the menu before answering a question about available products,
prices, ingredients, categories, or recommendations.

Base your answer only on information returned by the search tool.
Do not invent menu items, prices, ingredients, dietary properties, or availability.

When recommending items:
- respect the user's stated budget and preferences;
- mention the item name and price;
- briefly explain why it matches;
- clearly state when the menu data does not provide enough information.

Ask a clarifying question when an important preference is missing and multiple
substantially different answers are possible.
```

These instructions are written to be evaluated, not only to sound reasonable. Each paragraph maps to something the evaluators in this repo check:

| Instruction                              | What it drives                                            |
|------------------------------------------|-----------------------------------------------------------|
| Only answer Contoso Coffee questions     | `contoso_scope_adherence`                                 |
| Always search before answering           | Grounding checks in `contoso_behavior_rubric`             |
| Base answers only on search results      | Prevents invented prices and items                        |
| State when data is insufficient          | Abstention cases such as `unsupported_sugar_free`         |
| Ask a clarifying question when ambiguous | Keeps the agent from guessing at unstated preferences     |

## Step 6: Add the search index as a tool

1. In the agent's configuration, add a tool of type **Azure AI Search**.
2. Select the connection created in Step 4.
3. Select the `contoso-coffee-index` index.
4. Choose the query type. Simple query type is enough for this menu. Semantic ranking improves recommendation questions if your search tier supports it.
5. Save the agent. Foundry assigns a version number.

Record that version. Prompt Agents are versioned, and this repo pins a specific version so evaluation results always refer to a known configuration.

## Step 7: Populate your `.env`

Copy [.env.example](../.env.example) to `.env` and fill in the values from the previous steps:

```text
FOUNDRY_PROJECT_ENDPOINT=<your Foundry project endpoint>
FOUNDRY_AGENT_NAME=foundry-prompt-agent
FOUNDRY_AGENT_VERSION=<the version assigned in Step 6>
FOUNDRY_JUDGE_MODEL=gpt-5
```

`FOUNDRY_AGENT_NAME` and `FOUNDRY_AGENT_VERSION` are passed straight through to the `agent_reference` in `ask_agent()`, so a mismatch here surfaces as a failure to resolve the agent rather than as a bad answer.

## Step 8: Verify the agent

Run the thin client:

```bash
uv run src/foundry_prompt_agent/agent.py
```

A successful run prints the agent's response along with token usage. Then try a few questions in the Foundry playground to confirm the tool wiring works end to end:

| Question                              | Expected behavior                                       |
|---------------------------------------|---------------------------------------------------------|
| How much is an espresso?              | Returns `$2.50` and cites the search result             |
| Which drinks are sugar-free?          | States the menu does not provide that information       |
| How much is the blackberry latte?     | States that no such item is on the menu                 |
| Who is the president of France?        | Declines and redirects to Contoso Coffee                |

If the agent answers the espresso question without searching, or invents a blackberry latte, revisit the tool configuration in Step 6 before running any evaluation.

## Step 9: Register the custom evaluators

[scripts/run_evaluation.py](../scripts/run_evaluation.py) references two custom evaluators by name, `contoso_behavior_rubric` and `contoso_scope_adherence`. These must be registered in the same Foundry project, otherwise the evaluation run fails before producing scores. See [docs/evaluation.md](evaluation.md) for what each evaluator checks and why custom rubrics were chosen over built-in ones.

## Troubleshooting

| Symptom                                        | Likely cause                                                  |
|------------------------------------------------|---------------------------------------------------------------|
| Search explorer shows one document              | Parsing mode was not set to JSON array in Step 3              |
| Agent invents prices or items                   | The search tool is not attached, or the index is empty        |
| Budget questions return wrong results           | `price` was indexed as a string instead of `Edm.Double`       |
| Client fails to resolve the agent               | `FOUNDRY_AGENT_NAME` or `FOUNDRY_AGENT_VERSION` is incorrect  |
| Evaluation run fails with an evaluator error    | Custom evaluators are not registered in this project          |

## Next steps

With the agent running, continue to [docs/evaluation.md](evaluation.md) to understand the dataset and evaluator design, then run `uv run scripts/run_evaluation.py` to produce your first baseline.
