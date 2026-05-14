# Taskpool pre-add checklist

Use before `brain_task_orchestrator.py add` for external-link ingest or task decomposition.

1. Classify the item
- repo/article/reference analysis
- parent-task decomposition
- direct implementation/audit
- advisory/observation only

2. Decide if it belongs in the pool now
- actionable now -> create task
- worth tracking but not immediate -> likely P3
- too vague / duplicate -> refine or do not add yet

3. Decide priority before add
- P1: strong leverage on core Hermes/taskpool/control-plane/reliability/recoverability
- P2: useful and actionable, but not first-wave leverage
- P3: reserve/observation/backlog value

4. Decide architecture landing zone
- local-brain / taskpool / control-plane
- prompt/context/memory
- loop/tool registry/subagent
- skill graph / provider / policy / safety

4.5. For GitHub repo ingest, gather minimum source evidence first
- repo metadata: description, primary language, stars/forks/issues, topics
- README / project positioning summary
- search for existing taskpool duplicates or near-duplicates
- write three judgments before add:
  - priority tier + leverage reason
  - architecture landing zone + why
  - anti-drift / acceptance / boundary constraints

If the repo is relevant to Hermes itself, phrase the task as “analyze X and optimize Hermes Y” rather than as a passive repo summary.

5. For split tasks, decide order and boundaries
- schema/protocol before automation
- define serial vs parallel boundaries
- note blocked-by relation in the task body/frontmatter if no dedicated field exists

Suggested dependency language when fields are absent:
- "Recommended order: A -> B -> C"
- "Blocked by: packet schema definition"
- "Parallel boundary: can run after task A; independent from task C"

6. Multimodel triage for high-impact work
- do it before add
- record whether it merely triggered or actually converged
- do not equate trigger-rate with completed analysis

7. Verify the created task is governed, not raw
- priority already chosen
- acceptance already scoped
- anti-drift check already present
- dependency/order intent already visible
- no promise to 'sort later' unless explicitly unavoidable
