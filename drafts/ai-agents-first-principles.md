# Everyone's Talking About AI Agents. I Read the Papers So You Don't Have To.

*A conversational, slightly nerdy tour through the five papers that built the field — and why most "AI agent" articles get it wrong.*

---

There's something weird happening in tech right now.

Open any tech newsletter and you'll see "AI agents" mentioned three times before you finish your coffee. Every startup is "agentic." Every framework promises "autonomous agents." Every conference has at least one keynote about how agents will replace half your engineering team by Q3.

And yet — and this is the part that drives me crazy — almost nobody can clearly explain what an AI agent actually *is*. Not in the marketing sense. In the actual, technical, "if I open the box, what's inside?" sense.

I went hunting for a good explanation. Read about thirty articles. Most of them said some variation of: "An AI agent is an LLM that uses tools and has memory and can complete tasks autonomously." Which is technically true, in the same way that saying "a car is a metal box with wheels that takes you places" is technically true. It tells you nothing about how the engine works.

So I went to the papers. The actual, citable, peer-reviewed papers that built this field. There turn out to be five of them that matter, and once you've read them, the whole "agent" thing stops feeling like magic and starts feeling like... well, like a clever idea that was bound to happen the moment language models got good enough.

Let me walk you through them. No frameworks, no marketing, no "10 best agent tools of 2026." Just the ideas.

## The Realization That Started It All

Picture it: late 2022. ChatGPT just dropped. Everyone is having a great time asking it to write poems and explain quantum mechanics. But a few researchers at Princeton notice something interesting — and slightly weird.

When you ask GPT a hard question, it sometimes just... makes stuff up. Confidently. With great prose. Total nonsense. The classic hallucination problem.

But here's the thing they noticed: if you tell GPT to "think step by step," it gets better. And if you tell it to "think step by step AND tell me when you need to look something up," it gets *much* better. The act of separating "thinking" from "doing" — generating reasoning traces in between actions — turned out to be transformative.

That observation became a paper called **ReAct: Synergizing Reasoning and Acting in Language Models** (Yao et al., ICLR 2023). It's the foundation of everything that followed.

The core insight is almost insultingly simple. Instead of asking an LLM to answer in one shot, you teach it to write something like:

> *Thought:* I need to find out who directed the movie that won Best Picture in 2019.
> *Action:* search("Best Picture 2019 winner")
> *Observation:* "Green Book won Best Picture at the 91st Academy Awards."
> *Thought:* Now I need the director of Green Book.
> *Action:* search("Green Book director")
> *Observation:* "Peter Farrelly directed Green Book."
> *Thought:* I have the answer.
> *Final answer:* Peter Farrelly.

That's it. That's the whole loop. Reason. Act. Observe. Repeat until done.

And here's why it works: the LLM is no longer trying to generate the answer from its (potentially outdated, potentially wrong) parametric memory. It's *thinking out loud* and reaching for tools when it needs them. The reasoning grounds the actions, and the actions ground the reasoning. They prop each other up.

This is the agent loop. Every AI agent you've ever seen — every Claude Code session, every LangChain agent, every Cursor autocomplete — is, at its core, running some variant of this loop. The implementations get fancier. The prompt templates get more elaborate. But the bones are the same.

If you remember nothing else from this article, remember this: **an AI agent is just a language model running in a loop with the ability to use tools.** Everything else is engineering.

## The Awkward Question: How Does It Know Which Tools Exist?

OK so the LLM can call tools. Cool. But how does it actually *know* which tools are available, and how to format the call correctly, and which tool to pick for which problem?

For about a year after ReAct, the answer was "really long prompts." You'd write something like "You have access to these 12 tools, here are their names, here are their descriptions, here's the JSON format, please use them correctly, oh and here are some examples, please don't mess up the syntax." And it kind of worked. Most of the time.

But it was clearly a hack. And in February 2023, Meta published a paper that pointed at something deeper: **Toolformer: Language Models Can Teach Themselves to Use Tools**.

The Toolformer idea is wild when you think about it. They asked: what if, instead of telling the model how to use tools at inference time, we baked the knowledge into the model itself during training?

Their method goes like this. Take a bunch of regular text. Have the model insert "tool calls" at points where it thinks a tool would be helpful — for example, replacing "the population of France is 67 million" with "the population of France is [Calculator(France population) → 67 million]." Then check whether the prediction with the tool call is *more accurate* than without. Keep the helpful insertions. Throw away the rest. Fine-tune the model on the result.

The model learns, in a self-supervised way, when reaching for a tool actually helps and when it doesn't. By the end, it's automatically calling calculators, search APIs, translation services, and date-lookup functions exactly when needed.

This was the moment "tool use" stopped being a prompt-engineering trick and became a *capability*. Every modern model — GPT-5, Claude, Gemini, the open-source ones — has tool use baked in at the training level. It's not bolted on afterwards. It's part of who they are.

The reason this matters for agent design is subtle but important: you're no longer fighting the model to call tools correctly. The model *wants* to call tools when they help. Your job as an agent builder is mostly to give it good tools and get out of the way.

## The Skill Library: Where Things Got Wild

Now we get to my favorite paper. I genuinely think it's one of the most underappreciated pieces of AI research from 2023.

Picture Minecraft. You're an AI. Your goal is open-ended: "thrive." That's it. No objectives, no quests, no win condition. Just exist in this voxel world and figure stuff out.

This is the setup for **Voyager: An Open-Ended Embodied Agent with Large Language Models** (Wang et al., 2023). And what they did with it changed how I think about agents.

Voyager is built around three ideas. The first is an **automatic curriculum** — the agent literally asks itself "what should I learn next?" based on what it's accomplished so far. It might say: "I have wood. I should make a crafting table. After that, I should learn to make a wooden pickaxe. After that, stone tools." It's setting its own goals, hierarchically.

The second idea is a **skill library**. When Voyager figures out how to do something — say, "find iron underground" — it doesn't just do it once and forget. It writes the solution as executable code, gives it a name, and saves it. Next time the agent needs iron, it doesn't re-derive the procedure. It just calls `mine_iron_ore()` like a function from a library it's been building all its life.

The third idea is **iterative self-improvement through error feedback**. When the code fails (because Minecraft is full of edge cases), the agent reads the error message, reasons about what went wrong, and rewrites the code. The skill gets better over time, like an engineer refactoring legacy code.

Here's why this is huge: Voyager is, to my knowledge, the first AI agent that exhibited something resembling **lifelong learning**. It doesn't just complete tasks. It accumulates a vocabulary of capabilities and uses that vocabulary to take on harder tasks. After a few hours of running, it knows things its earlier self didn't.

This is the prototype for everything we now call "memory" in agent systems. The vector databases, the retrieval-augmented memories, the persistent state — all of it is descended from the basic Voyager idea. Don't make the agent re-derive everything from scratch. Let it remember.

When I see articles that say "AI agents need memory," what they're really saying — though they almost never explain it this way — is "AI agents need something like Voyager's skill library, generalized to non-code tasks, scaled to many users, and integrated with a retrieval system that can find the right skill at the right moment."

## The Paper That Made Agents Feel Human

Around the same time as Voyager, a Stanford team published something even weirder: **Generative Agents: Interactive Simulacra of Human Behavior** (Park et al., 2023).

They built a tiny town. Twenty-five AI characters living in it. Each one had a name, a personality, a daily routine. They could see each other, talk to each other, plan their days, remember their conversations.

What happened next was the kind of thing that makes you stare at the ceiling at 2am. The agents started organizing parties. They formed friendships. One agent decided to run for mayor and held campaign events. Another fell in love. They held a Valentine's Day gathering — *entirely on their own initiative*, because one agent had decided it would be fun and started inviting others.

None of this was scripted. The researchers gave each agent a basic memory system, a daily planning loop, and the ability to reflect on their experiences. The emergent social behavior just... happened.

The paper's contribution to agent research is the **memory architecture**. Specifically, they introduced the idea of **hierarchical memory** with three layers:

The first layer is **observations**: raw events as they happen ("at 3pm, I saw Mei in the cafe"). These get logged constantly.

The second layer is **reflections**: higher-order summaries the agent generates by reviewing its observations ("Mei seems to spend a lot of time at the cafe. She might be a regular there"). Reflections are themselves stored as memories, and they're what give the agent a sense of *patterns* rather than just events.

The third layer is **plans**: the agent's intentions about the future, generated by considering its current state, recent observations, and longer-term goals.

When the agent needs to recall something — say, when deciding whether to invite Mei to a party — it queries this memory system using a relevance score that combines how recent the memory is, how important it is, and how relevant it is to the current situation.

This three-layer model — observe, reflect, plan — is the cognitive architecture inside basically every "personal AI assistant" being built today. The Cluely, the Rewinds, the Limitless Pendants, the rumored OpenAI hardware — they all owe a debt to this paper, even if their builders don't know it.

## The Uncomfortable Part: Why Most Agents Don't Work

I've made it sound like this is all figured out. It isn't.

Here's the thing nobody likes to talk about: **most AI agents in production right now are kind of bad**. Not because the ideas are wrong, but because the math is brutal.

Imagine your agent has a 95% success rate on each individual step. That sounds great, right? An A in school. Now imagine the agent needs to chain 20 steps together to complete a task. The probability that *every step* succeeds is 0.95 to the 20th power, which is... 35.8%.

A 95% reliable agent fails at multi-step tasks almost two-thirds of the time. And 95% per-step is generous. Real agents on real tasks often hit 80-90% per step, which means a 10-step task succeeds maybe 35% of the time, and a 20-step task is essentially a coin flip with poor odds.

This is called the **compounding error problem**, and it's the single biggest reason your favorite "AI agent" demos look great in the controlled YouTube video and then fall on their face when you try to use them for your actual work.

There are a few directions the research community is pushing on. One is **verifier models** — separate models whose only job is to check whether the agent is on track and yell at it when it goes off the rails. Another is **plan-then-execute** architectures, where the agent commits to a high-level plan up front and then runs each step against the plan, rather than re-deciding at every turn (this dramatically reduces the cost of compounding errors because mistakes get caught at the plan level, not the action level). A third is **self-correction loops** — letting the agent observe its own outputs and revise them, similar to how Voyager rewrote its code when it failed.

But the honest truth is: in 2026, we don't yet have a great answer. The labs that are actually shipping useful agents — Cursor, Claude Code, Devin — are doing it through a mix of really good tool design, conservative scoping ("the agent can only edit one file at a time"), and a lot of human-in-the-loop checkpoints. The fully autonomous "give it a goal and walk away" agent is still mostly a research artifact.

If you're building an agent and it doesn't work, you're not stupid. The math is just hard.

## The Formula That Actually Holds Up

After reading all these papers, here's the cleanest mental model I've found for what an AI agent actually is:

**Agent = LLM + Memory + Planning + Tool Use, all running in a loop.**

The LLM is the brain. It generates the reasoning, picks the actions, interprets the observations.

Memory is what lets the agent learn from its history — both the short-term "what did I just do?" and the long-term "what have I learned over time?" Without memory, every interaction starts from scratch and the agent can't improve.

Planning is the ability to decompose a goal into steps. Some agents plan once at the start (cheap, brittle). Some replan after every action (expensive, robust). Most useful agents are somewhere in between.

Tool use is the connection to the world. Without tools, the agent is just an LLM in a box, capable of nothing but talking. With tools, it can read files, query databases, call APIs, control browsers, write code. The tools are where the rubber meets the road.

And the loop is what ties it all together. Without the loop, you have a chatbot. With the loop, you have an agent. Everything else — every framework, every protocol, every wrapper library — is an attempt to make this loop more reliable, more debuggable, or easier to write.

I find this framing weirdly liberating. Once you stop thinking of "AI agents" as some new mysterious technology and start thinking of them as "an LLM in a while loop with some tools," the whole space gets a lot less intimidating. You can build one in an afternoon. (You probably already have, even if you didn't call it that.)

## Where This Is All Going

If I had to bet on where AI agents are headed over the next year or two, here's what I'd put money on.

**Memory is going to get a lot better.** The current state of the art — vector databases plus a retrieval prompt — is clearly a stopgap. There are papers coming out monthly with fancier ideas: graph-based memory (MAGMA), memory operating systems (EverMemOS), agents that learn how to manage their own memory through reinforcement learning (MemRL). The space is exploding because the bottleneck is obvious: you can't have a useful long-running agent without good memory, and we haven't figured out good memory yet.

**Tool protocols will standardize.** Right now, every framework has its own way of describing tools to LLMs. MCP (Model Context Protocol) — the thing I wrote about in another article — is becoming the de facto standard. Within a year, "writing a tool for an AI agent" will be as standardized as writing a REST endpoint. This is going to dramatically lower the barrier to entry.

**Compounding errors will be addressed at the model level, not the framework level.** The hacks we use today — verifiers, plan-then-execute, self-correction — are workarounds for the fact that LLMs aren't reliable enough at single-step decisions. When the underlying models get better at admitting uncertainty and asking for help, multi-step reliability will improve dramatically. This is already happening with Claude Opus 4.6 and similar frontier models.

**Most "AI agents" you're hearing about today won't exist in two years.** Not because the technology is going away, but because the marketing will move on and the surviving products will just be called "software." The same way we don't call Photoshop "AI image editing software" even though it has tons of AI features.

The real question, the one I think is worth obsessing over, isn't "will AI agents be a big deal?" They already are, even if most of them are quietly embedded in tools you already use. The question is: **what becomes possible when language models are reliable enough that the agent loop just works?**

That's the world we're building toward. And the five papers I just walked you through are the foundation it's being built on.

If you've made it this far, you officially understand AI agents better than 90% of the people writing about them. Go build something weird with this knowledge. The space is wide open, the tools are free, and most of the "experts" are just repackaging the same five papers without telling you they exist.

Now you know.

---

*The papers, for the curious: ReAct (Yao et al., 2022), Toolformer (Schick et al., 2023), Voyager (Wang et al., 2023), Generative Agents (Park et al., 2023). Read them in that order. They're surprisingly readable and they'll change how you think about this whole space.*

---

**Tags:** `artificial-intelligence`, `ai-agents`, `llm`, `programming`, `machine-learning`
