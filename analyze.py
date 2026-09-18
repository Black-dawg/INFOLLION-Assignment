"""
Pricing Refactor Regression Analysis
=====================================
Analysis script used to investigate pricing differences between v1 and v2.
"""

import pandas as pd
import numpy as np
import json

# Load data
df = pd.read_csv('pricing_diff.csv')
df['diff'] = df['v2_total'] - df['v1_total']
df['abs_diff'] = df['diff'].abs()

print(f"Dataset: {len(df)} orders, {len(df.columns)} columns")
print(f"Categories: {sorted(df['category'].unique())}")
print()

# ── Q1: Naive count ──────────────────────────────────────────────────────────
q1 = int((df['v2_total'] != df['v1_total']).sum())
print(f"Q1: Rows where v2_total != v1_total = {q1}")
print()

# ── Explore diffs by category ────────────────────────────────────────────────
print("Diff stats by category:")
for cat in sorted(df['category'].unique()):
    s = df[df['category'] == cat]
    large = (s['abs_diff'] > 0.05).sum()
    print(f"  {cat:12s}  n={len(s):5d}  mean_diff={s['diff'].mean():+8.4f}  "
          f"max|diff|={s['abs_diff'].max():.4f}  large(>$0.05)={large}")
print()

# ── Identify the bug ────────────────────────────────────────────────────────
# Filter for large diffs excluding the intentional books change
large_diff = df[(df['abs_diff'] > 0.05) & (df['category'] != 'books')]
print(f"Large diffs (|diff| > $0.05, excl. books): {len(large_diff)}")
print(f"  Categories:  {large_diff['category'].value_counts().to_dict()}")
print(f"  Express:     {large_diff['express'].value_counts().to_dict()}")
print()

# ── Q2: Affected orders ─────────────────────────────────────────────────────
bug_mask = (df['category'] == 'fragile') & (df['express'] == True)
bug_orders = df[bug_mask]
q2 = len(bug_orders)
print(f"Q2: Affected orders (fragile + express) = {q2}")
print(f"    All overcharged (v2 > v1): {(bug_orders['diff'] > 0).all()}")
print(f"    Min overcharge: ${bug_orders['diff'].min():.2f}")
print(f"    Max overcharge: ${bug_orders['diff'].max():.2f}")
print()

# ── Q3: Total overcharge ────────────────────────────────────────────────────
q3 = round(bug_orders['diff'].sum(), 2)
print(f"Q3: Total overcharge = ${q3:.2f}")
print()

# ── Q4: Baseline sanity check ───────────────────────────────────────────────
clean = df[(df['category'] != 'books') & ~bug_mask]
q4 = clean['abs_diff'].mean()
print(f"Q4: Mean |diff| for non-bug, non-books orders = ${q4:.6f}")
print(f"    (Rounded: ${round(q4, 2):.2f})")
print(f"    Max |diff| in this group: ${clean['abs_diff'].max():.4f}")
print()

# ── Q5: Bug pattern analysis ────────────────────────────────────────────────
y = bug_orders['diff'].values
x = bug_orders['distance_km'].values
slope, intercept = np.polyfit(x, y, 1)
pred = slope * x + intercept
ss_res = np.sum((y - pred) ** 2)
ss_tot = np.sum((y - y.mean()) ** 2)
r2 = 1 - ss_res / ss_tot
print(f"Q5 analysis: overcharge = {slope:.4f} * distance_km + {intercept:.2f}")
print(f"    R² = {r2:.4f}  (distance explains {r2*100:.1f}% of variance)")
print(f"    Conclusion: fragile handling surcharge applied TWICE for express orders")
print()

# ── Write answers.json ───────────────────────────────────────────────────────
answers = {
    "q1_naive_nonzero_count": q1,
    "q2_affected_count": q2,
    "q2_affected_category": "fragile",
    "q3_total_overcharge": q3,
    "q4_baseline_mean_abs_diff": round(q4, 2)
}
with open('answers.json', 'w') as f:
    json.dump(answers, f, indent=2)
print("answers.json written:")
print(json.dumps(answers, indent=2))
