---
name: check-allocation-drift
description: Compare portfolio weights with user-defined targets, bands or a prior dated allocation. Use for drift, divergence and contribution-only rebalancing scenarios, while distinguishing changes in diversification.
---

# Check allocation drift against a target

Answer “How far have I moved from my intended allocation?” State what the comparison is against. **Drift** measures distance from a reference. **Diversification** describes concentration across issuers, funds, sectors or other risk factors. A portfolio can match its target exactly and still depend on one issuer. If the user says “diverged” without giving a reference, show current weights, ask for their target or baseline, and explain any measurable concentration. Comparing with a previous allocation measures change over time. Label it as such unless that allocation was the user's target.

## Make the weights comparable

Use the user's dated targets or bands, their cash policy and the account scope. For Trading 212, take each account's unfiltered `list_positions` and `get_account_summary` in the same observation window. Check private broker IDs for duplicated accounts and keep demo values separate. Use each position’s `walletImpact.currentValue` in `walletImpact.currency`. Distinguish available cash from reserved or Pie cash, and record any discrepancy between account total, invested value and cash. Use one dated FX basis or compare accounts separately.

Match the target's denominator and bucket definitions. A target for **invested assets only** excludes cash from both weights and target amounts. A target including cash uses the relevant whole-portfolio value. Group by mutually exclusive categories. Use the fund itself for a fund-level target, or decompose it once with dated fund-manager weights for an underlying-allocation target. Keep unclassified exposure visible. When a residual could belong to a target bucket, give a range or coverage gap before calling a breach. If the targets do not sum to 100%, establish whether the remainder is explicitly unassigned or the target covers one sleeve. Do not silently rescale.

## Calculate the gap

| Measure | Calculation |
| --- | --- |
| Actual weight | Bucket value divided by the matched total. A zero or negative denominator needs an amount-based explanation. |
| Drift in percentage points | Actual weight in percent minus target in percent. Positive means overweight. A change from 20% to 25% is +5 percentage points, or +25% relative to the target if that metric was requested. |
| Amount above target | Current bucket value minus target fraction times the matched total. Give the currency. |
| Band result | Compare actual weight with the user's lower and upper limits, retaining unrounded values. Confirm how any relative tolerance applies to each target. If no limits are supplied, rank gaps by size and leave breach status open. |

Show a short table with bucket, actual, target, drift and any band result. Rank by absolute drift to surface material changes. State which exposures could remain concentrated despite being on target. For long-only portfolios with complete, exclusive targets and no external flow, half the sum of absolute amount gaps is the one-way value to move to reach the targets, before costs.

If the user asks what a new contribution could change, make it a **hypothetical** calculation. For a fully invested new contribution, use the enlarged total, calculate each bucket's target amount and subtract its existing value. Restrict new allocations to the available contribution, state how you prioritised shortfalls, and show residual drift. Distinguish uninvested new cash and pre-existing cash already included in the denominator. Close with the data, target or classification that most affects the conclusion. [FINRA on allocation and diversification](https://www.finra.org/investors/investing/investing-basics/asset-allocation-diversification)
