# Who Agrees About How Agents Fail — copy deck

Every number here comes from `data/results-rev3.json` or `data/results-rev4.json`.
Where a figure has a known weakness, the weakness goes in the same sentence as the
figure. That is a design rule, not a disclaimer.

**Nothing in this deck has been posted.** These are drafts for approval.

---

## THE ONE-LINE VERSION

We published a null result, then refuted it ourselves two days later. The null was
about the size of our annotators, not about the thing we were annotating.

## THE NUMBERS THAT CARRY THE STORY

> **0.173 → 0.360 → 0.598.** Agreement on a fourteen-cell failure taxonomy, at
> 2–12B, at 70B, and at frontier. Same transcripts, same prompt, same parser —
> reused as literal objects, because rewriting any of them would have meant
> comparing two studies instead of two tiers.

> **0.047, CI [−0.065, 0.157].** How well the published reference labels agree
> *with themselves*, on duplicated traces the released file already contains. The
> interval contains zero.

> **−0.014.** How well four frontier models agree with those published labels.
> They agree with *each other* at 0.598.

> **$3.00.** Total cost of the run that overturned our own headline.

---

## SOCIAL — SHORT (X / Bluesky / Mastodon)

**A. The correction (lead with this one)**

> We published a null: LLMs don't agree when applying a multi-agent failure
> taxonomy. α = 0.173.
>
> Two days later we refuted ourselves. Every annotator we'd used was 2–12B.
>
> At frontier scale: 0.598.
>
> The null was about model size. It was never about the taxonomy.

**B. The sharper one**

> While checking our own null, we scored the reference labels against themselves —
> the released dataset already contains duplicated traces with conflicting
> annotations.
>
> α = 0.047. CI contains zero.
>
> Four frontier models agree with each other at 0.598, and with those labels
> at −0.014.

**C. The methods one**

> Our first frontier run said the big models "couldn't follow the output format."
>
> They could. `max_tokens=300` was being eaten entirely by reasoning tokens —
> `finish_reason: length`, empty content. Same call, reasoning off: 5 tokens.
>
> Open one raw payload before believing any claim about a model's competence.

**D. The one about limitations sections**

> We controlled the prompt. We controlled the framing. We controlled the question
> shape. We ran the expensive checks.
>
> Then one variable we'd already written into our own limitations section
> overturned the headline.
>
> The limitations section is where your next experiment is.

## SOCIAL — MEDIUM (LinkedIn)

> **We refuted our own result two days later.**
>
> There's a published taxonomy of the fourteen ways multi-agent AI systems fail.
> A taxonomy is only worth something if two annotators applying it to the same
> transcript land in the same place — so we asked whether language models do.
>
> Six open-weight models, real transcripts, one instruction each. Agreement came
> back at 0.173. Close to nothing. We'd been careful: every model passed a framing
> test before it coded anything, and we'd checked that the shape of the question
> barely moved the number. So we published the null.
>
> Buried in that write-up's limitations section was a sentence noting every model
> we used was between 2 and 12 billion parameters. We wrote it down and moved on,
> the way you do.
>
> Two days later we ran it again on bigger models. Same transcripts, same prompt,
> same parser. 0.360 at 70B. 0.598 at frontier. The gap between top and bottom
> tier is 0.425, with a confidence interval nowhere near zero.
>
> Our null was a fact about model size. It was never a fact about the taxonomy.
>
> The thing we found on the way is sharper. The released dataset contains
> duplicated transcripts carrying conflicting labels — accidentally, a reliability
> experiment. Scored, the published labels agree with themselves at 0.047, with a
> confidence interval containing zero. Four frontier models agree with each other
> at 0.598 and with those labels at −0.014.
>
> That's not a claim the models are right. There's no ground truth here — that's
> the whole problem. It's a claim about which reference is more stable, and you
> can measure it without any ground truth at all.
>
> Protocols, pre-registrations, raw model output and scoring code are public.

## SOCIAL — COMMUNITY (Discord / forum)

> New on the bench: we asked whether LLMs agree when applying a published
> multi-agent failure taxonomy, got a null, then found the null was about our
> annotators being small rather than about the taxonomy. 0.173 at 2–12B, 0.598 at
> frontier.
>
> Underneath it: the reference labels score 0.047 against themselves on the
> released file's own duplicate traces, while four frontier coders agree with each
> other and not with those labels.
>
> Both pre-registrations, both results docs and the raw scorer output are up. The
> whole run cost $3.
>
> Happy to argue about any of it — particularly the choice to record a missing
> vendor as unavailable rather than substitute another model after seeing the
> other scores.

---

## GUARDRAILS FOR ANY VERSION OF THIS COPY

Do not let these drop out, in any platform edit:

1. **0.598 is still below 0.667**, the conventional floor for reliable annotation.
   This is not "frontier models solved it." It is a different world from 0.173,
   which is a different and smaller claim.
2. **Concordance, never accuracy.** Nothing here says the models are correct. There
   is no ground truth. The claim is about stability of a reference.
3. **The vendor gap is real.** No Google coder — the pre-registered one refuses to
   run with reasoning disabled, and substituting after seeing other scores is the
   discretion pre-registration exists to prevent. Two vendors, not three.
4. **n = 24 traces**, short-to-medium, three strata. Small.
5. **The correction is the story.** Do not quietly drop rev 3.1 and present only
   the frontier numbers — the sequence is the point.
