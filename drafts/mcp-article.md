# I Built an MCP Server in 30 Minutes. Here's Why Every AI Agent Needs One.

*Forget complex frameworks. The Model Context Protocol lets your AI agent talk to any tool with a few lines of Python.*

---

You've probably heard about AI agents. Everyone is building them. LangChain, CrewAI, AutoGen — the framework list grows weekly.

But here's what nobody talks about: **how does your agent actually connect to external tools?**

Most tutorials hand-wave this part. They hard-code API calls, duct-tape JSON schemas, and pray the LLM formats its output correctly. It works in demos. It breaks in production.

There's a better way. It's called **MCP** (Model Context Protocol), and once you see it, you can't go back.

## What Is MCP (And Why Should You Care)?

MCP is an open protocol — originally created by Anthropic, now under the Linux Foundation — that standardizes how AI models interact with external tools and data sources.

Think of it as **USB-C for AI agents**. Before USB-C, every device had its own charger. Before MCP, every agent framework had its own way to wire up tools. MCP gives you a single, universal interface.

Here's why it matters:

- **Write once, use everywhere.** An MCP server works with Claude, GPT, Gemini, or any MCP-compatible client.
- **No more glue code.** Tools describe themselves — their inputs, outputs, and what they do.
- **Security built-in.** The protocol enforces a request/approval flow. Your agent can't silently do things behind your back.

Today there are 2,300+ public MCP servers covering databases, browsers, APIs, file systems, and more. But the best part? **Building your own takes 30 minutes.**

Let me prove it.

## What We'll Build

We're going to build an MCP server that tracks trending Medium articles. It will expose two tools:

1. **`get_trending`** — Fetch top posts from Medium by tag, with clap counts and engagement metrics
2. **`get_tag_summary`** — Get a quick summary of what's hot across multiple tags

By the end, your AI agent will be able to say: *"What's trending in AI agents on Medium right now?"* — and get a real answer.

## Step 1: Set Up the Project

You'll need Python 3.10+ and `uv` (the fast Python package manager):

```bash
# Create the project
uv init medium-mcp
cd medium-mcp

# Set up a virtual environment
uv venv
source .venv/bin/activate

# Install the MCP SDK
uv add "mcp[cli]"
```

That's it for dependencies. We won't use `requests` or `httpx` — Python's built-in `urllib` handles everything we need.

## Step 2: Build the MCP Server

Create a file called `server.py`:

```python
import html
import re
from xml.etree import ElementTree as ET
from urllib.request import urlopen, Request
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("medium-trending")

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
FEED_URL = "https://medium.com/feed/tag/{tag}"
```

That's the entire setup. `FastMCP` handles all the protocol boilerplate — JSON-RPC, session management, schema generation. You just write Python functions.

## Step 3: Add the RSS Fetcher

```python
def fetch_tag_feed(tag: str) -> list[dict]:
    """Fetch the latest posts from a Medium tag RSS feed."""
    url = FEED_URL.format(tag=tag)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    
    with urlopen(req, timeout=15) as resp:
        tree = ET.parse(resp)
    
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    posts = []
    
    for item in tree.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        author = item.findtext("dc:creator", "", ns).strip()
        pub_date = item.findtext("pubDate", "").strip()
        tags = [c.text for c in item.findall("category") if c.text]
        
        # Clean tracking params
        link = re.sub(r"\?source=rss[^&]*", "", link)
        
        posts.append({
            "title": html.unescape(title),
            "link": link,
            "author": html.unescape(author),
            "pub_date": pub_date,
            "tags": tags,
        })
    return posts
```

Nothing MCP-specific here — just standard RSS parsing. The magic comes next.

## Step 4: Add Engagement Metrics

Here's something most people don't know: **Medium embeds clap counts directly in the article HTML.** No API key needed.

```python
def fetch_claps(url: str) -> dict:
    """Scrape engagement metrics from a Medium article page."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=15) as resp:
            page = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return {"claps": None, "responses": None}
    
    claps_match = re.search(r'"clapCount":(\d+)', page)
    resp_match = re.search(
        r'"postResponses":\{"__typename":"PostResponses","count":(\d+)\}', page
    )
    reading_match = re.search(r'"readingTime":([\d.]+)', page)
    
    return {
        "claps": int(claps_match.group(1)) if claps_match else None,
        "responses": int(resp_match.group(1)) if resp_match else None,
        "reading_time": f"{round(float(reading_match.group(1)))} min" if reading_match else None,
    }
```

Medium's client-side JavaScript stores a `clapCount` field in the page's Apollo state. A simple regex pulls it out in milliseconds.

## Step 5: Wire It Up as MCP Tools

This is where it all comes together. **Two decorators. That's it.**

```python
@mcp.tool()
def get_trending(tag: str, top_n: int = 5) -> list[dict]:
    """Get the top trending Medium posts for a given tag.
    
    Args:
        tag: Medium tag to search (e.g. 'ai-agents', 'llm', 'python')
        top_n: Number of top posts to return (default: 5)
    """
    posts = fetch_tag_feed(tag)
    
    # Enrich with engagement metrics
    for post in posts[:top_n]:
        metrics = fetch_claps(post["link"])
        post.update(metrics)
    
    # Sort by claps
    posts.sort(key=lambda p: p.get("claps") or 0, reverse=True)
    return posts[:top_n]


@mcp.tool()
def get_tag_summary(tags: list[str]) -> dict:
    """Get a summary of trending topics across multiple Medium tags.
    
    Args:
        tags: List of Medium tags to analyze (e.g. ['ai-agents', 'llm', 'python'])
    """
    all_tags = []
    total_posts = 0
    
    for tag in tags:
        posts = fetch_tag_feed(tag)
        total_posts += len(posts)
        for post in posts:
            all_tags.extend(post["tags"])
    
    # Count tag frequency
    from collections import Counter
    tag_counts = Counter(all_tags).most_common(10)
    
    return {
        "tags_searched": tags,
        "total_posts_found": total_posts,
        "trending_topics": [{"tag": t, "count": c} for t, c in tag_counts],
    }
```

Look at what `FastMCP` does for you:

- **`@mcp.tool()`** registers the function as an MCP tool
- The **docstring** becomes the tool's description (what the LLM reads to decide when to use it)
- **Type hints** become the JSON schema (the LLM knows `tag` is a string and `top_n` is an integer)
- The **return value** is automatically serialized

No manual schema writing. No JSON-RPC handlers. No boilerplate.

## Step 6: Run It

Add the entry point:

```python
if __name__ == "__main__":
    mcp.run()
```

That's the complete server. Run it:

```bash
python server.py
```

## Step 7: Connect It to Claude

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

```json
{
  "mcpServers": {
    "medium-trending": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

Restart Claude Desktop. You'll see a hammer icon indicating your tools are loaded.

Now ask Claude: **"What's trending in AI agents on Medium?"**

Claude will:
1. Recognize it needs the `get_trending` tool
2. Call it with `tag="ai-agents"`
3. Get back real data with clap counts
4. Summarize the results in natural language

No prompt engineering. No output parsing. It just works.

## The Bigger Picture

This 80-line server is a toy example, but the pattern scales. Here's what MCP servers look like in the real world:

| Server | What It Does |
|--------|-------------|
| `mcp-github` | Read issues, PRs, create branches |
| `mcp-postgres` | Query databases with natural language |
| `mcp-browser` | Navigate and extract web content |
| `mcp-slack` | Read channels, send messages |

Every one of these follows the same pattern: **expose Python functions with type hints and docstrings, let MCP handle the rest.**

## Why Not Just Use Function Calling?

Fair question. OpenAI, Anthropic, and Google all support function calling. Why add a protocol layer?

Three reasons:

1. **Portability.** A function-calling tool is locked to one provider. An MCP server works with any client.
2. **Composability.** Your agent can connect to *multiple* MCP servers simultaneously. A Slack server + GitHub server + your custom server = a powerful agent.
3. **Separation of concerns.** The tool author doesn't need to know about the LLM. The LLM doesn't need to know about the tool's internals. MCP is the contract between them.

## What I'd Build Next

If this article resonated, here are natural next steps:

- **Add a `search_articles` tool** that searches Medium by keyword (using their unofficial API)
- **Deploy it as a remote server** using Streamable HTTP transport instead of stdio
- **Build a daily digest agent** that uses the MCP server to find trending posts and draft article ideas

The MCP ecosystem is growing fast. The question isn't whether to learn it — it's whether you want to be building MCP servers or still writing glue code when everyone else has moved on.

---

*The complete source code for this MCP server is available on [GitHub](https://github.com/ebarkhordar/medium). Star it if you found this useful.*

---

**Tags:** `ai-agents`, `mcp`, `llm`, `python`, `artificial-intelligence`
