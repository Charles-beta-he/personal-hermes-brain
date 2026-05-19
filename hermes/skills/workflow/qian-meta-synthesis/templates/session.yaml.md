# Meta-synthesis session template

```yaml
meta_synthesis_session:
  problem: ""
  desired_state: ""
  constraints: []
  source_packet:
    verified: []
    uncertain: []
    missing: []
  qualitative_hypotheses:
    - claim: ""
      owner_brain: research
      confidence: 0.0
      falsifier: ""
  quantitative_checks:
    - owner_brain: dev
      artifact: ""
      command_or_path: ""
      result: WARN
  dissent:
    - participant: ""
      objection: ""
      resolution: deferred
  handback:
    requesting_brain: ""
    implementation_brain: dev
    return_to_brain: ""
    delivered_artifact: ""
    invocation_example: ""
    verification_results: []
    known_limits: []
  decision: split
```
