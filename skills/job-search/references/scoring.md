# Scoring reference

What `jobsearch score` does, so a reader can reproduce any number. All weights are in `jobsearch.config.json` under `scoring`; edit the config, not the code.

## Arithmetic (per role)

Start at 40, then:

| Signal | Config key | Effect |
|---|---|---|
| Company tier 1, 2, 3 (aliases match whole words for short names) | `tier_points` | add points; unlisted company adds 0 |
| Domain families found in the title or description (a family counts once) | `domain_families`, `domain_cap` | add each matching family's points, total capped |
| Negative families: a keyword in the title, or twice in the description | `negative_families` | subtract 10 (title) or 6 (description), total floor -20 |
| A level word in the title | `level_words`, `level_bonus` | add; none present subtracts `no_level_penalty` |
| Title looks like your role | `title_match`, `title_miss_penalty` | add the first matching group's points, else subtract the penalty |
| Location in `home_locations` / remote / elsewhere | `home_bonus`, `remote_bonus`, `out_of_area_penalty` | add, add, subtract |
| Posted within `new_badge_days` | `fresh_bonus` | add |
| Listed minimum pay at or above `comp_bonus_min` / below `comp_low_penalty_below` | | +5 / -6 |

The result is capped at `base_cap` (97). The scorer saturates: several strong roles can tie near the cap. That is why you calibrate by reading.

## Scope gate

`scope_gate.in_phrases` are signals the work is in your target field; `out_phrases` (per sub-field) and `title_out` signal an adjacent sub-field you are not targeting. A role is OUT when it has at least two distinct out-signals in one sub-field and more out-signals than in-signals. OUT roles are capped at Stretch / Watch however high they score; below the floor they are Filtered. The reason is stored on the row (`scope_reason`).

## Buckets

| Bucket | Rule (defaults in the example config) |
|---|---|
| Strongest Fit | score at least `strongest_min` (80), not scope-gated out |
| Strong Fit | at least `strong_min` (65) |
| Stretch / Watch | at least `stretch_min` (60), plus every scope-gated role at or above it |
| Filtered | below `stretch_min`; appears in the Filtered tab with the score and the signals |

Within a bucket: score, then newest posted first.

## Calibration (your part)

The scorer cannot tell whether a description needs expertise the candidate lacks. Read descriptions in this order, up to the budget (8 in a full run, 3 in a quick run):

1. Roles that reached Strongest or Strong on title evidence, so a keyword trap is caught before it ranks high.
2. Roles within 10 points of a bucket edge.
3. Roles that resemble a declined or closed tracker entry (to see if it is the same requisition).

Fetch one description at a time (title and description fields only, offset and limit of 1) so the dataset never enters the conversation. For each change, add to `adjustments.json`:

```json
[{"company": "Example Co", "title_contains": "Bring-up", "delta": -12,
  "reason": "Description requires 5+ years of RTL design, which the profile cannot evidence."}]
```

Use `link_contains` instead of company and title when you have the posting id. `set` replaces the score; `delta` adds. `bucket` may be given to force a bucket. Everything not read stays as the scorer left it: say so in the notes ("description not read") and do not call it Strongest on the title alone.

Record the arithmetic and each adjustment in `--notes` so the dashboard footer lets a reader reproduce the run.
