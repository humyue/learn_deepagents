> ## Documentation Index
> Fetch the complete documentation index at: https://docs.langchain.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Quickstart

> Build your first deep agent in minutes

This guide walks you through creating your first deep agent with file system tools and subagent capabilities. You will build a research agent that can conduct research and write reports.

<Prompt description="Build the Deep Agents research quickstart" icon="sparkles" actions={["copy"]}>
  Build a Deep Agents research agent in this working directory by following the Deep Agents quickstart.

  ## Step 1: Read the guide

  Detect whether this project uses Python or TypeScript/JavaScript. Fetch and follow the matching page; treat it as the source of truth for package names, model strings, search-tool setup, and code:

  * Python: [https://docs.langchain.com/oss/python/deepagents/quickstart.md](https://docs.langchain.com/oss/python/deepagents/quickstart.md)
  * TypeScript: [https://docs.langchain.com/oss/javascript/deepagents/quickstart.md](https://docs.langchain.com/oss/javascript/deepagents/quickstart.md)

  ## Step 2: Install dependencies

  Install `deepagents` (and `langchain` / `@langchain/core` on TypeScript) with the package manager already used in this project. Add Tavily only if the user is not using a Google, OpenAI, or Anthropic built-in provider search tool.

  ## Step 3: Configure model credentials

  Check for a supported provider API key (for example `GOOGLE_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`). If none is set, ask the user which provider to use, then stop and wait while they create a key and set it in the shell or a `.env` file. Do not invent, hardcode, or commit API keys. If they need Tavily, ask them to set `TAVILY_API_KEY` the same way.

  ## Step 4: Implement the research agent

  Follow the quickstart steps in order:

  1. Create the internet search tool (prefer the provider built-in search tool when the chosen model supports it; otherwise use Tavily).
  2. Call `create_deep_agent` with the search tool, a `provider:model` string (or initialized model) from the guide, and the research system prompt shown on the page.
  3. Optionally enable LangSmith tracing by asking the user to set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` themselves.
  4. Run the agent on a sample research query from the guide and print the final response.

  ## Rules

  * Stay scoped to this quickstart. Do not add Managed Deep Agents deployment, evals, or unrelated frameworks.
  * Prefer provider built-in web search when available; use Tavily only when needed.
  * Ask rather than guess when a secret, provider choice, or project convention is unclear.
</Prompt>

<Tip>
  **Using an AI coding assistant?**

  * Install the [LangChain Docs MCP servers](/use-these-docs) to give your agent access to up-to-date LangChain documentation and examples.

      <Prompt description="Connect LangChain docs MCP servers" icon="plug" actions={["copy"]}>
        Connect both LangChain documentation MCP servers to my coding agent so it can look up current LangChain, LangGraph, and LangSmith docs and API reference.

        Servers to add:

        * `docs-langchain`: [https://docs.langchain.com/mcp](https://docs.langchain.com/mcp)
        * `reference-langchain`: [https://reference.langchain.com/mcp](https://reference.langchain.com/mcp)

        Detect which agent or editor I am using (Claude Code, Cursor, Codex CLI, Claude Desktop, Deep Agents Code, VS Code, Antigravity, or another MCP-compatible client). Use the matching setup from [https://docs.langchain.com/use-these-docs.md](https://docs.langchain.com/use-these-docs.md):

        * Claude Code: `claude mcp add --transport http` for each server (project scope by default; use `--scope user` only if I ask for global access).
        * Codex CLI: `codex mcp add` with each server URL.
        * Cursor, Deep Agents Code, VS Code, or Antigravity: merge both entries into the MCP settings JSON using the field names shown on that page for my client.
        * Claude Desktop: add both URLs under Settings > Connectors.

        Do not invent alternate MCP URLs. After configuring, confirm both servers are listed and reachable.
      </Prompt>
  * Install [LangChain Skills](https://github.com/langchain-ai/langchain-skills) to improve your agent's performance on LangChain ecosystem tasks.

      <Prompt description="Install LangChain Skills" icon="puzzle" actions={["copy"]}>
        Install LangChain Skills for my coding agent so it can perform better on LangChain, LangGraph, and Deep Agents tasks.

        Use the Agent Skills installer from [https://github.com/langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills):

        ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
        npx skills add langchain-ai/langchain-skills --skill '*' --yes
        ```

        If I ask for a global install instead, use:

        ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
        npx skills add langchain-ai/langchain-skills --skill '*' --yes --global
        ```

        Detect which agent or editor I am using. If I use Claude Code and prefer the plugin path, follow the marketplace install from that repository README (`/plugin marketplace add` then `/plugin install`). Do not invent alternate skill package names or install URLs. After installing, confirm the skills are available to the agent.
      </Prompt>
</Tip>

## Prerequisites

Before you begin, make sure you have an API key from a model provider (e.g., Gemini, Anthropic, OpenAI).

<Note>
  Deep Agents require a model that supports [tool calling](/oss/python/langchain/models#tool-calling). See [customization](/oss/python/deepagents/customization#model) for how to configure your model.
</Note>

## Step 1: Install dependencies

<CodeGroup>
  ```bash pip theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  pip install deepagents
  ```

  ```bash uv theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  uv init
  uv add deepagents
  uv sync
  ```
</CodeGroup>

<Note>
  Google, OpenAI, and Anthropic all provide built-in web search tools: no extra package or API key required. If you use a different provider or prefer [Tavily](https://tavily.com/) for search, install the Tavily package as well:

  ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  pip install tavily-python
  ```
</Note>

## Step 2: Set up your API keys

<Tabs>
  <Tab title="Google">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    export GOOGLE_API_KEY="your-api-key"
    ```
  </Tab>

  <Tab title="OpenAI">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    export OPENAI_API_KEY="your-api-key"
    ```
  </Tab>

  <Tab title="Anthropic">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    export ANTHROPIC_API_KEY="your-api-key"
    ```
  </Tab>

  <Tab title="OpenRouter">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    export OPENROUTER_API_KEY="your-api-key"
    export TAVILY_API_KEY="your-tavily-api-key"
    ```
  </Tab>

  <Tab title="Fireworks">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    export FIREWORKS_API_KEY="your-api-key"
    export TAVILY_API_KEY="your-tavily-api-key"
    ```
  </Tab>

  <Tab title="Baseten">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    export BASETEN_API_KEY="your-api-key"
    export TAVILY_API_KEY="your-tavily-api-key"
    ```
  </Tab>

  <Tab title="Ollama">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    # Local: Ollama must be running on your machine
    # Cloud: Set your Ollama API key for hosted inference
    export OLLAMA_API_KEY="your-api-key"
    export TAVILY_API_KEY="your-tavily-api-key"
    ```
  </Tab>

  <Tab title="Other">
    ```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    # Set the API key for your provider
    export <PROVIDER>_API_KEY="your-api-key"
    export TAVILY_API_KEY="your-tavily-api-key"
    ```

    Deep Agents work with any [LangChain chat model](/oss/python/deepagents/models#supported-models). Set the API key for your provider.
  </Tab>
</Tabs>

<Tip>
  **Using LangSmith Gateway**

  The [LangSmith Gateway](/langsmith/llm-gateway) routes most major providers through LangSmith. You can [bring your own provider keys](/langsmith/llm-gateway-quickstart#send-a-request), or use [Gateway Credits](/langsmith/llm-gateway-credits) to access models without a provider key.
</Tip>

## Step 3: Create a search tool

Google, OpenAI, and Anthropic offer built-in web search tools that run server-side: no extra package or API key needed. Pass a provider tool dict directly to `create_deep_agent`.

<Tabs>
  <Tab title="Provider search (recommended)">
    <CodeGroup>
      ```python Google theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from deepagents import create_deep_agent

      # Google's built-in search — no extra install or API key needed
      internet_search = {"google_search": {}}
      ```

      ```python OpenAI theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from deepagents import create_deep_agent

      # OpenAI's built-in web search — no extra install or API key needed
      internet_search = {"type": "web_search"}
      ```

      ```python Anthropic theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
      from deepagents import create_deep_agent

      # Anthropic's built-in web search — no extra install or API key needed
      internet_search = {"type": "web_search_20260209", "name": "web_search"}
      ```
    </CodeGroup>
  </Tab>

  <Tab title="Tavily (any provider)">
    ```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
    import os
    from typing import Literal

    from tavily import TavilyClient
    from deepagents import create_deep_agent

    tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


    def internet_search(
        query: str,
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general",
        include_raw_content: bool = False,
    ):
        """Run a web search"""
        return tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
    ```
  </Tab>
</Tabs>

## Step 4: Create a deep agent

Pass your search tool and model to `create_deep_agent`. Pass a `model` string in `provider:model` format, or an [initialized model instance](/oss/python/deepagents/models#configure-model-parameters). See [supported models](/oss/python/deepagents/models#supported-models) for all providers and [suggested models](/oss/python/deepagents/models#suggested-models) for tested recommendations.

<CodeGroup>
  ```python Google theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  # System prompt to steer the agent to be an expert researcher
  research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

  You have access to an internet search tool as your primary means of gathering information.

  ## `internet_search`

  Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
  """

  agent = create_deep_agent(
      model="google_genai:gemini-3.6-flash",
      tools=[internet_search],
      system_prompt=research_instructions,
  )
  ```

  ```python OpenAI theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  # System prompt to steer the agent to be an expert researcher
  research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

  You have access to an internet search tool as your primary means of gathering information.

  ## `internet_search`

  Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
  """

  agent = create_deep_agent(
      model="openai:gpt-5.5",
      tools=[internet_search],
      system_prompt=research_instructions,
  )
  ```

  ```python Anthropic theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  # System prompt to steer the agent to be an expert researcher
  research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

  You have access to an internet search tool as your primary means of gathering information.

  ## `internet_search`

  Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
  """

  agent = create_deep_agent(
      model="anthropic:claude-sonnet-5",
      tools=[internet_search],
      system_prompt=research_instructions,
  )
  ```

  ```python OpenRouter theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  # System prompt to steer the agent to be an expert researcher
  research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

  You have access to an internet search tool as your primary means of gathering information.

  ## `internet_search`

  Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
  """

  agent = create_deep_agent(
      model="openrouter:z-ai/glm-5.2",
      tools=[internet_search],
      system_prompt=research_instructions,
  )
  ```

  ```python Fireworks theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  # System prompt to steer the agent to be an expert researcher
  research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

  You have access to an internet search tool as your primary means of gathering information.

  ## `internet_search`

  Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
  """

  agent = create_deep_agent(
      model="fireworks:accounts/fireworks/models/glm-5p2",
      tools=[internet_search],
      system_prompt=research_instructions,
  )
  ```

  ```python Baseten theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  # System prompt to steer the agent to be an expert researcher
  research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

  You have access to an internet search tool as your primary means of gathering information.

  ## `internet_search`

  Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
  """

  agent = create_deep_agent(
      model="baseten:zai-org/GLM-5.2",
      tools=[internet_search],
      system_prompt=research_instructions,
  )
  ```

  ```python Ollama theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
  # System prompt to steer the agent to be an expert researcher
  research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

  You have access to an internet search tool as your primary means of gathering information.

  ## `internet_search`

  Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
  """

  agent = create_deep_agent(
      model="ollama:north-mini-code-1.0",
      tools=[internet_search],
      system_prompt=research_instructions,
  )
  ```
</CodeGroup>

## Step 5: Set up LangSmith tracing

[LangSmith](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-deepagents-quickstart) provides you with visibility into your agent's execution, allowing you to view tool calls, subagent delegation, and LLM responses.

Sign up at [smith.langchain.com](https://smith.langchain.com?utm_source=docs\&utm_medium=cta\&utm_campaign=langsmith-signup\&utm_content=oss-deepagents-quickstart), create an API key, and set these environment variables:

```bash theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY="your-langsmith-api-key"
```

## Step 6: Run the agent

```python theme={"theme":{"light":"catppuccin-latte","dark":"catppuccin-mocha"}}
result = agent.invoke({"messages": [{"role": "user", "content": "What is langgraph?"}]})

# Print the agent's response
print(result["messages"][-1].content)
```

## How does it work?

Your deep agent automatically:

1. **Conducts research** by calling the `internet_search` tool to gather information.
2. **Manages context** by using file system tools ([`write_file`](/oss/python/deepagents/overview#virtual-filesystem-access), [`read_file`](/oss/python/deepagents/overview#virtual-filesystem-access)) to offload large search results.
3. **Spawns subagents** as needed to delegate complex subtasks to specialized subagents.
4. **Synthesizes a report** to compile findings into a coherent response.

To add structured task planning with `write_todos`, opt in with [`TodoListMiddleware`](https://reference.langchain.com/python/langchain/agents/middleware/todo/TodoListMiddleware). See [Task planning](/oss/python/deepagents/overview#task-planning).

## Examples

For agents, patterns, and applications you can build with Deep Agents, see [Examples](https://github.com/langchain-ai/deepagents/tree/main/examples).

## Streaming

Deep Agents have built-in [streaming](/oss/python/langchain/event-streaming) for real-time updates from agent execution using LangGraph.
This allows you to observe output progressively and review and debug agent and subagent work, such as tool calls, tool results, and LLM responses.

## Next steps

Now that you've built your first deep agent:

* **Customize your agent**: Learn about [customization options](/oss/python/deepagents/customization), including custom system prompts, tools, and subagents.
* **Add long-term memory**: Enable [persistent memory](/oss/python/deepagents/memory) across conversations.
* **Deploy to production**: Use [Managed Deep Agents](/langsmith/python/managed-deep-agents-overview) to create, run, and operate deep agents in LangSmith.
* **Test and evaluate**: Use [LangSmith evaluation](/langsmith/evaluation-quickstart) to run automated tests and measure your agent's performance against a dataset.

***

<div className="source-links">
  <Callout icon="terminal-2">
    [Connect these docs](/use-these-docs) to your agent of choice via MCP for real-time answers.
  </Callout>

  <Callout icon="edit">
    [Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/deepagents/quickstart.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
  </Callout>
</div>
