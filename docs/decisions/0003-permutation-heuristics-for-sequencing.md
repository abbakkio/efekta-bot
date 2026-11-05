# ADR-003: Permutation Heuristics and Grammar Scoring for Word Sequencing

## Status
Accepted

## Date
2026-11-05

## Context
Efekta sentence reconstruction exercises (`ef-sequencing-tap-option-task`) present scrambled tokens that must be tapped in correct grammatical order. For an 8-word sentence, full combinatorial enumeration yields $8! = 40,320$ permutations, which is prohibitive for brute-force clicking in a real browser.

Additionally, Angular CDK Drag-and-Drop applies `cdk-drag cdk-drag-disabled` to token `<li>` elements even in tap-to-order tasks, causing false identification as column drag tasks.

## Decision
1. **Selector Disambiguation**: Restrict CDK drag handling exclusively to `ef-sequencing-sort-column-task` when tap-to-order containers are absent.
2. **Anchor Pinning**:
   - Pinned Prefix: Capitalized word tokens are assigned as the first token.
   - Pinned Suffix: Punctuation-terminated tokens (`.`, `?`, `!`) are assigned as the final token.
3. **Grammar Scoring Matrix**: Middle tokens are sorted by a bigram transition score prioritizing:
   - Subject pronouns $\to$ auxiliary verbs / 3rd-person singular verbs (`He aims`, `She hopes`, `I expect`).
   - Phrasal expressions $\to$ `to` markers (`aims to`, `looking to`, `planning to`).
   - `to` $\to$ infinitive base verbs (`to move`, `to increase`, `to improve`).
   - Prepositional phrases and collocations (`up in the company`, `my skill set`).
4. **Failure Tracking**: Evaluated sequences that are rejected by the UI are stored in `_failed_permutations` and pruned from candidate generation.

## Consequences
- **Pros:**
  - Dramatically reduces search space from $O(N!)$ to 1–3 attempts in the vast majority of cases.
  - Eliminates false positives between tap-to-order and column drag tasks.
- **Cons:**
  - Requires maintaining grammar heuristics for edge-case sentence structures.
