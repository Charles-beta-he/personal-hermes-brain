# Confidence Calibration for AI Agent Outputs

## Why Calibrate?

LLMs are typically overconfident. A self-reported confidence of 0.9 may only
correspond to 70% actual accuracy. Calibration aligns reported confidence with
observed precision.

## Calibration Techniques

### 1. Temperature Scaling (Post-Hoc)
Apply temperature T > 1 to logits before softmax.
Optimal T found via validation set (typically T=1.5-3.0 for code tasks).
Simple but requires held-out labeled data.

### 2. Platt Scaling
Fit logistic regression: `calibrated_p = 1 / (1 + exp(A*logit + B))`
A, B learned on held-out labeled data.
Works well when you have ground truth from code review outcomes.

### 3. Expected Calibration Error (ECE)
Bin predictions by confidence (0-0.1, 0.1-0.2, ..., 0.9-1.0).
`ECE = sum(|accuracy_in_bin - confidence_in_bin| * bin_size)`
Target ECE < 0.05 for production systems.

### 4. Conformal Prediction
Non-parametric, distribution-free calibration.
Produces prediction sets with guaranteed coverage.
"With 90% probability, this finding is in the set of true bugs."
Adaptive: narrower sets for easy cases, wider for uncertain ones.

### 5. Self-Consistency Sampling
Sample N responses from same agent with temperature > 0.
Confidence = fraction of samples that agree.
More robust than single-point confidence estimates.

## Bayesian Agent Reputation

Track each agent's historical precision/recall per bug type:
- Use Beta(alpha, beta) distributions updated after human feedback
- Agent reputation = alpha / (alpha + beta)
- Weight new findings by agent reputation
- Cold start: Beta(2, 2) = uniform prior with mild regularization

## Feedback Loop

1. Present findings to human reviewer
2. Track accept/reject for each finding
3. Update agent reputation scores
4. Adjust thresholds based on observed precision
5. Log everything for later analysis

## Practical Calibration Pipeline

```
[Raw Agent Output]
    → Self-reported confidence (prompt-engineered)
    → Cross-agent agreement boost
    → Historical precision weighting (if available)
    → Severity-based threshold adjustment
    → Final filtered output
```

Without historical data, use:
```
final_conf = (self_conf * 0.4) + (agreement_ratio * 0.6)
```

With historical data, use:
```
final_conf = (self_conf * 0.3) + (agreement_ratio * 0.3) + (historical_precision * 0.4)
```

## References

- SonarQube quality gate system (industry standard)
- GitHub Copilot confidence calibration (conformal prediction)
- DeepCode/Snyk Code multi-model ensemble
- Facebook Infer (separation logic with confidence scoring)
- Google Tricorder (human-in-the-loop calibration)
