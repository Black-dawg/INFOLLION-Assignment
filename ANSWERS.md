# Pricing Refactor Regression — Answers

## Q1: Naive count of rows where `v2_total != v1_total`

**Answer: 16,000 rows** out of 20,000 have `v2_total != v1_total`.

This number is **not** a useful measure of "how many orders are actually affected by a real bug" for two reasons:

1. The refactor intentionally changed the internal summation order, so tiny floating-point rounding differences (±$0.01–$0.02) appear on the vast majority of orders. These are harmless numerical noise, not real pricing errors.
2. The intentional per-kg rate change for the `books` category also causes every books order to differ. Counting all non-equal rows lumps together harmless rounding noise, the approved books change, and the actual bug — making the number meaningless as a bug metric.

---

## Q2: Number of orders affected by a genuine pricing regression

**Answer: 985 orders** are affected by the genuine bug.

**Shared input conditions — all 985 affected orders have:**
- `category = fragile`
- `express = True`

No other combination of category and express flag shows any meaningful pricing difference beyond floating-point noise (≤$0.02). The affected orders include both coupon (`SAVE10`) and non-coupon orders, so the coupon is not a factor in triggering the bug.

---

## Q3: Total dollar amount of overcharge

**Answer: $19,779.14 total overcharge** across the 985 affected orders.

All affected orders were **overcharged** (v2_total > v1_total). The per-order overcharge ranges from ~$5.08 to ~$34.98, with a mean of ~$20.08.

---

## Q4: Sanity check — average difference for non-bug, non-books orders

**Answer: The mean absolute `|v1_total − v2_total|` difference for orders that are NOT affected by the bug AND NOT in the `books` category is $0.01 (0.0099).**

This confirms the finding in Q2 is a real, distinct pattern:
- The 15,680 "clean" orders (non-bug, non-books) have a mean absolute difference of only ~$0.01 — consistent with harmless floating-point rounding noise.
- The 985 bug-affected orders (fragile + express) have a mean difference of **$20.08** — over 2,000× larger, and always positive (overcharged).
- The difference is not "everything is a little different" — it is a sharp, categorical divide. The bug-affected group is an unmistakable outlier.

---

## Q5 (Bonus): What is the likely code-level bug?

**The fragile handling surcharge is being applied twice for express orders in the refactored code (v2).**

Evidence:
- The overcharge correlates almost perfectly with `distance_km` (R² = 0.989) and is nearly independent of `weight_kg`.
- A linear regression of the overcharge gives: **overcharge ≈ $4.85 + $0.098 × distance_km**.
- This fits a "fragile handling surcharge" consisting of a ~$4.85 flat fee plus ~$0.098/km distance-based fee.
- Only `fragile + express` orders are affected. Fragile non-express orders show no bug. Express non-fragile orders show no bug.

**Most likely explanation:** During the refactor, the code path that computes the total for express fragile orders applies the fragile category surcharge **twice** — once during the base price calculation and again when applying the express multiplier or in a separate surcharge step. In the old code (v1), the fragile surcharge was correctly applied only once. The refactored code likely moved the fragile surcharge calculation into a function or block that gets invoked both by the base-price logic and the express-processing logic, resulting in a double charge.

---

## Investigation Process

- **Step 1:** Loaded the CSV (20,000 rows, 8 columns) and computed `diff = v2_total - v1_total` for every order.
- **Step 2:** Counted naive non-equal rows → 16,000 of 20,000 rows differ (Q1). Immediately clear this is mostly noise.
- **Step 3:** Grouped by `category` and computed diff statistics. Found `books` has consistent positive diffs (~$2.47 mean) — the documented intentional change. Found `fragile` has a suspiciously high mean diff and large max absolute diff.
- **Step 4:** Filtered for large differences (|diff| > $0.05) excluding books → found exactly **985 rows**, all sharing `category=fragile` and `express=True`.
- **Step 5:** Verified that ALL 985 fragile+express orders have overcharges ≥ $5.08, and zero fragile+express orders have small diffs. The bug affects every single fragile+express order.
- **Step 6:** Checked the baseline: non-bug, non-books orders have max |diff| of only $0.02, confirming the fragile+express pattern is distinct.
- **Step 7:** Ran regression on the overcharge amount vs. order features. Distance explains 98.9% of the variance in overcharge (R² = 0.989). Weight has negligible effect.
- **Step 8:** The regression coefficients (~$4.85 base + ~$0.098/km) suggest the overcharge equals the fragile handling surcharge itself — i.e., it's being applied twice.
- **Dead end:** Initially checked if `coupon` was involved in the bug. SAVE10 orders have slightly lower overcharges on average, but this is simply because the coupon discount reduces the base on which the surcharge is computed — the coupon is not a trigger condition.
- **Dead end:** Briefly considered whether weight played a role, but the weight coefficient in the regression was negligible (~$0.003/kg), ruling it out.
