# Your LLM Judge Is Lying To You. Here's the Bias Tax You're Paying.

*Everyone is using GPT-5 or Claude to grade their AI outputs. Almost nobody is checking whether the grader can actually grade.*

---

Every AI team I've talked to in the last six months has the same evaluation pipeline.

They generate outputs from their model. They feed those outputs to GPT-5 or Claude Opus 4.6 with a prompt that says something like "rate this response from 1 to 10." They average the scores. They put it on a dashboard. They ship.

This is called LLM-as-a-judge, and it's everywhere. Every eval framework supports it. Every "AI observability" startup pitches it. Every internal benchmark at every AI company runs on it. The original paper that legitimized the technique back in 2023 (Zheng et al., MT-Bench) reported that the judge model agreed with human raters about 80% of the time. Same as humans agree with each other. Case closed, right?

Not even close.

The papers that came out after that one are a horror show. And if you're using LLM judges in production without reading them, you're flying blind. Let me walk you through what's actually broken.

## The Position Bias You Probably Already Have

Here's a fun experiment. Take an LLM judge. Show it response A and response B, and ask which is better. Then run the same prompt again with the responses swapped. Position A is now the old position B.

In a perfect world, the judge picks the same response both times. The actual world is not that world.

The paper *Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge* (Shi et al., IJCNLP-AACL 2025) ran this test across multiple judge models, multiple benchmarks (MTBench, DevBench), and thousands of pairwise comparisons. The result: position consistency, the rate at which a judge picks the same response when you flip the order, varies wildly. Some judges flip their answer more than 30% of the time on identical content.

The variable that matters most isn't the task. It isn't the response length. It's *which judge model you picked*. Some judges are stable. Some are coin flips with extra steps. Most teams using LLM-as-judge have never measured this for their setup.

The standard fix is to run every comparison twice with the order swapped and only count it as a "win" if the judge picks the same response both ways. This is called *consistency filtering*, and it roughly doubles your eval cost. Most teams skip it. Their dashboards reflect this.

## The Self-Preference Problem

Now the really uncomfortable one.

Researchers ran a clean experiment a while back. Take a strong model. Have it generate a response. Have a different model generate a response to the same prompt. Ask a third party (humans) to rate them as equivalent. Now ask the original model to judge. It systematically rates its own response higher.

The really damning part: the strength of this bias correlates almost linearly with how well a model can recognize its own outputs. The better it can tell "I wrote this" vs "something else wrote this," the more it tilts toward its own work.

Follow-up work pinned down the mechanism. Judges quietly score text by how surprising it looks under their own distribution. A model's own outputs are, by definition, unsurprising to it. So they get higher scores. It's not vanity. It's a direct artifact of how the scoring works.

What this means in practice: if you're using GPT-5 to evaluate GPT-5 outputs against Claude outputs, GPT-5 wins on your eval and you have no idea how much of that is real and how much is the judge cheating for its sibling. Same in reverse. Same when DeepSeek grades DeepSeek. Same when Gemini grades Gemini.

The mitigation is annoying but obvious: use a different model family as the judge than the model you're evaluating. Or use multiple judges from different families and average. Both options cost money. Most teams don't bother.

## The Bias Zoo

Once you start looking, the biases multiply. The CALM benchmark catalogues twelve distinct ones. A few highlights, in plain English:

- **Verbosity bias:** longer answers win, regardless of quality. The judge confuses thoroughness with correctness.
- **Authority bias:** if a response cites a famous name or institution, even a fake one, scores go up.
- **Bandwagon bias:** tell the judge "90% of people prefer answer A," and it shifts toward A.
- **Sentiment bias:** cheerful, confident-sounding answers beat neutral or hedged ones, even when the hedged ones are more accurate.
- **Refinement-aware bias:** if a response is framed as "the improved version of an earlier draft," the judge rates it higher even when the content is identical.

Every frontier model tested (yes, including the latest GPT-5, Claude Opus, Gemini 3) exhibits measurable bias on most of these. The numbers aren't cherry-picked edge cases. They're from a systematic benchmark with thousands of paired comparisons.

If your eval prompt looks like *"You are a strict grader. Rate this response from 1 to 10 based on accuracy and clarity"*, congratulations, you have built a verbosity meter with a sentiment filter on top.

## Why The Original 80% Number Was Misleading

The original paper isn't wrong. It's just narrower than people remember.

The 80% agreement number comes from a specific setting: pairwise comparisons of chatbot responses on open-ended questions, with humans and LLMs both agreeing the responses were "different enough" to compare. In that regime, the judge does match human preferences as well as humans match each other.

But the way most teams use LLM judges in 2026 is not that. It's:

- Single-response scoring, not pairwise (worse calibration).
- Specialized domains like code, finance, legal (where human inter-rater agreement is itself low).
- Production logs at scale, not curated eval sets.
- Often the same model judging its own family's outputs.

In every one of those settings, the 80% number from MT-Bench is an upper bound that you almost certainly do not hit. The honest assumption is something like 60-70% agreement with what a thoughtful human would say, with systematic skews in the directions I described above.

That's still useful. It is *not* "as good as a human."

## The Fixes That Actually Work

I'm not here to tell you to throw out LLM-as-judge. It's the only scalable evaluation method we have, and the alternative (human review) is slow, expensive, and has its own biases. The point is to use it with eyes open.

Here's what's been shown to actually move the needle:

**Pairwise over scoring.** Pairwise comparisons ("which is better, A or B?") are more reliable than absolute scoring ("rate this 1-10"). This has been replicated repeatedly. If your eval is single-response scoring, switching to pairwise against a fixed baseline is the cheapest improvement you can make.

**Position swapping.** Always run pairwise comparisons twice with positions swapped. Only count results where the judge agrees with itself. The cost is 2x. The bias removal is huge.

**Cross-family judging.** Don't use a model to judge its own family. If you're evaluating GPT-5 outputs, use Claude Opus or Gemini 3 as the judge. Better yet, use a panel of three judges from three families and require majority agreement.

**Calibration with anchor examples.** Include 2-3 hand-graded examples in the judge's prompt as a calibration anchor. This pulls the score distribution toward the right scale and reduces sentiment/verbosity drift.

**Spot-check with humans.** Sample 5% of judge decisions and have a human review them weekly. If judge-human disagreement is above 25%, you have a calibration problem and your dashboard is misleading you.

**Measure your own bias profile.** Run the position-swap test on your specific judge setup. It takes an afternoon. The CALM benchmark code is open source. You don't need to reinvent it. Just run it once, look at the numbers, and decide whether you can live with them.

## The Part Nobody Wants to Hear

Here's the part that's going to make some people uncomfortable.

Almost every "we improved our model by X%" claim from internal company blog posts in 2025 and 2026 is built on an LLM-judge eval pipeline that has none of the safeguards above. No position swapping. No cross-family judging. No human spot-checks. Often the judge is the same model family as the candidate.

That doesn't mean those claims are fake. Some of them are real improvements. But the *measurement* is noisier than the headline number suggests, and the direction of the noise is systematically biased toward "the new thing looks better than it is" because of confirmation effects in how people pick judges, write rubrics, and structure prompts.

If you're reading a benchmark result, the question to ask is: who was the judge, were they cross-family, were positions swapped, and did humans validate a sample? If the answer is "the same model family judged its own outputs against everything else, single-shot, no validation," the result is an internal sanity check, not a benchmark.

If you're building eval infrastructure for your own team, the question is the same. The good news is that the fixes are mostly mechanical and the papers above tell you exactly what to do. The bad news is that doing them properly costs 3-5x more than the naive setup, and a lot of teams will look at that cost and quietly not.

## The Punchline

LLM-as-a-judge is a power tool. It can grade ten thousand outputs in an afternoon for less than the cost of one human evaluator working a single hour. That's revolutionary, in the literal sense, and I don't want to walk it back.

But it's a power tool with a known set of failure modes that the research community has carefully documented and that the practitioner community has largely ignored. Position bias. Self-preference. Verbosity bias. Authority bias. Sentiment bias. They are all real, measurable, and present in the model you are using right now.

The teams that take eval seriously in 2026 are the ones treating LLM judges the way good labs treat any other instrument: calibrate it, characterize its noise, validate it against ground truth periodically, and report uncertainty bands instead of point estimates.

The teams that don't are the ones who will keep shipping "+12% on internal eval" press releases that don't replicate when anyone else tries to measure the same thing.

You can guess which group most teams are in.

---

**Tags:** `artificial-intelligence`, `llm`, `machine-learning`, `evaluation`, `ai-research`
