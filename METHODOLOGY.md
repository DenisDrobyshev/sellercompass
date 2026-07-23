# Methodology

The engine is a state machine over five stages. Each stage declares the inputs it consumes, the data it collects, the output it produces, and a gate: an explicit pass or fail condition computed from that data. The pipeline does not advance past a failed gate.

```
Discover -> Validate demand -> Competition -> Unit economics -> Decide
                  gate            gate            gate
```

Each section states the intent of a stage and then its contract. Where the v0 implementation differs from the intent, the difference is stated.

## Stage 1. Discover

Purpose: convert a stated interest into a short list of concrete candidate niches.

Inputs: first-batch budget, domains the user already knows, goal, risk tolerance.
Data: listings returned for the seed query.
Output: candidate niches, each with product count, median price and review total.
Gate: none. The stage is divergent and is expected to produce options.

Implementation: candidates are two and three word n-grams mined from product titles that specialise the seed. A candidate must appear in at least three listings to be reported.

## Stage 2. Validate demand

Purpose: establish that buyers exist before money is committed.

Inputs: a candidate niche.
Data: review totals across top listings, price distribution, review totals of earlier snapshots.
Output: demand score, price corridor, trend label (growing, flat, declining, unknown).
Gate: demand above the minimum threshold and not declining.

Implementation: review volume is used as the sales proxy, since Wildberries does not publish unit sales. Trend classification requires at least two snapshots. With a single snapshot the trend is unknown and the gate relies on demand level alone.

## Stage 3. Competition

Purpose: determine whether room to enter exists, and on what basis a newcomer could compete.

Inputs: a niche that passed stage 2.
Data: brand distribution, review volume per brand, price bands, ratings of leading listings, and the text of competitor reviews.
Output: concentration index, price corridor, list of openings.
Gate: the market is not saturated and at least one opening exists.

Implementation: concentration is the share of review volume held by the three largest brands, with a saturation threshold of 60 percent. Openings are listings with at least 200 reviews and a rating at or below 4.4, treated as evidence that buyers are not satisfied with the current leaders. Raw per-review text is protected on the reviews page and is not collected. What is available is Wildberries' own aggregated review summary and the aspect facets buyers discuss; `review_digest` reads those, and they are surfaced as customer voice in the stage output. `analyze_reviews`, which mines complaints from raw negative reviews, is implemented and tested but still awaits a raw-review source.

## Stage 4. Unit economics

Purpose: establish that the money works before inventory is ordered.

Inputs: the niche and its price corridor, the first-batch budget, optionally the purchase cost.
Data: category commission, logistics and acquiring fees, advertising cost per sale, tax, cost of goods.
Output: per-unit margin and margin share, first-batch size, required investment, projected profit and return on investment.
Gate: margin positive and at or above 10 percent, batch size at least 10 units.

Implementation: every fee assumption is a function parameter with a default. Cost of goods defaults to 35 percent of the selling price when the user does not supply a supplier quote.

## Stage 5. Decide

Purpose: produce a verdict that can be acted on.

Inputs: gate results of stages 2 to 4.
Output: a Go, Pivot or Kill verdict, a first-batch plan, a launch checklist.
Gate: none. The stage terminates the pipeline.

Decision rule: absence of demand yields Kill. Demand combined with a closed market or unworkable economics yields Pivot. All gates passing yields Go.

## Engine rules

Every gate reports the values it used. A verdict without its supporting numbers is not acceptable output.

A failed gate is a routing decision rather than an error. It returns the user to the last viable branch, normally another candidate from stage 1.

Gates are computed from data. A language model may interpret user intent, phrase a verdict in plain language, or extract themes from review text. It does not produce the numbers a gate depends on.
