# Who Agrees About How Agents Fail: copy deck

Every number here comes from `data/results-rev3.json` or `data/results-rev4.json`.
Where a figure has a known weakness, the weakness goes in the same sentence as the
figure. That is a design rule, not a disclaimer.

**Nothing in this deck has been posted.** These are drafts for approval.

**Voice:** written to the house anti-slop floor (`iris-brands/brands/nimbleco/VOICE.md`).
These are *not* in Matilde's voice and must not ship under her byline without her
pass. Her voice doc reserves that refusal explicitly, and the social register's
thread structure is still open for her ratification.

## The one-line version

We published a null result, then refuted it ourselves two days later. The null was
about the size of our annotators, not about the thing we were annotating.

## The numbers that carry the story

> **0.173, 0.360, 0.598.** Agreement on a fourteen-cell failure taxonomy at 2 to
> 12B, at 70B, and at frontier. Same transcripts, same prompt, same parser, reused
> as literal objects, because rewriting any of them would have meant comparing two
> studies instead of two tiers.

> **0.047, CI [−0.065, 0.157].** How well the published reference labels agree
> *with themselves*, on duplicated traces the released file already contains. The
> interval contains zero.

> **−0.014.** How well four frontier models agree with those published labels. They
> agree with *each other* at 0.598, which is still under the 0.667 the field treats
> as the floor for usable annotation.

## Social, short form

Built to fit inside 280 characters each. Verify the current limit per platform at
use time. **Thread structure is unratified** (social register, open item): post
these as standalone claims unless Matilde's pass defines a chain.

**A. The correction. Lead with this one.** (264 chars)

> We published a null: LLMs don't agree when applying a multi-agent failure
> taxonomy. α = 0.173.
>
> Two days later we refuted ourselves. Every annotator we'd used was 2 to 12B.
>
> At frontier scale: 0.598.
>
> The null was about model size. It was never about the taxonomy.

**B. The reference doesn't reproduce.** (260 chars)

> The released dataset already contains duplicated traces with conflicting
> annotations. So we scored the reference labels against themselves.
>
> α = 0.047. The CI contains zero.
>
> Four frontier models agree with each other at 0.598, and with those labels
> at −0.014.

**C. For anyone running models in a loop.** (269 chars)

> Our first frontier run said the big models "couldn't follow the output format."
>
> They could. max_tokens=300 was being eaten entirely by reasoning tokens:
> finish_reason=length, empty content. Same call, reasoning off, 5 tokens.
>
> Open one raw payload before believing it.

**D. On limitations sections.** (247 chars)

> We controlled the prompt, the framing, the question shape. We ran the expensive
> checks.
>
> Then one variable we had already written into our own limitations section
> overturned the headline.
>
> Your limitations section is where your next experiment is.

## Social, medium form (LinkedIn)

> **We refuted our own result two days later.**
>
> There is a published taxonomy of the fourteen ways multi-agent AI systems fail. A
> taxonomy is worth something only if two annotators applying it to the same
> transcript land in the same place, so we asked whether language models do.
>
> Six open-weight models, real transcripts, one instruction each. Agreement came
> back at 0.173, close to nothing. We had been careful: every model passed a framing
> test before it coded anything, and we had checked that the shape of the question
> moved the score by only 0.103. So we published the null.
>
> Buried in that write-up's limitations section was a sentence noting every model we
> used was between 2 and 12 billion parameters. We wrote it down and moved on, the
> way you do.
>
> Two days later we ran it again on bigger models. Same transcripts, same prompt,
> same parser. 0.360 at 70B. 0.598 at frontier. The gap between top and bottom tier
> is 0.425, with a confidence interval nowhere near zero, and 0.598 is still under
> the 0.667 the field treats as the floor for usable annotation.
>
> Our null was a fact about model size.
>
> What we found on the way is sharper. The released dataset contains duplicated
> transcripts carrying conflicting labels, which is accidentally a reliability
> experiment. Scored, the published labels agree with themselves at 0.047, with a
> confidence interval containing zero. Four frontier models agree with each other at
> 0.598 and with those labels at −0.014.
>
> That is not a claim the models are right. There is no ground truth here, which is
> the whole problem. It is a claim about which reference is more stable, and you can
> measure it without ground truth at all.
>
> Protocols, pre-registrations, raw model output and scoring code are public. The
> number we would most like someone to attack is 0.047.

## Social, community (Discord / forum)

> New on the bench. We asked whether LLMs agree when applying a published
> multi-agent failure taxonomy, got a null, then found the null was about our
> annotators being small rather than about the taxonomy. 0.173 at 2 to 12B, 0.598 at
> frontier, and 0.598 is still under the 0.667 floor.
>
> Underneath it: the reference labels score 0.047 against themselves on the released
> file's own duplicate traces, while four frontier coders agree with each other and
> not with those labels.
>
> Both pre-registrations, both results docs and the raw scorer output are up.
>
> Happy to argue about any of it, particularly the choice to record a missing vendor
> as unavailable rather than substitute another model after seeing the other scores.

## Guardrails for any version of this copy

Do not let these drop out in any platform edit:

1. **0.598 is still below 0.667**, the conventional floor for reliable annotation.
   This is not "frontier models solved it." It is a different world from 0.173,
   which is a smaller and different claim.
2. **Concordance, never accuracy.** Nothing here says the models are correct. There
   is no ground truth. The claim is about the stability of a reference.
3. **The vendor gap is real.** No Google coder. The pre-registered one refuses to
   run with reasoning disabled, and substituting after seeing other scores is the
   discretion pre-registration exists to prevent. Two vendors, not three.
4. **n = 24 traces**, short-to-medium, three strata. Small.
5. **The correction is the story.** Do not quietly drop rev 3.1 and present only the
   frontier numbers. The sequence is the point.
6. **Do not end on the best number.** The victory lap is banned in both the house
   floor and Matilde's list. Close on what a reader can check or attack.
