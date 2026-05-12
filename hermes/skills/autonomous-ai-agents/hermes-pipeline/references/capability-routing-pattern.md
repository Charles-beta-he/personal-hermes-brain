# Capability Routing — Model Selection by Task Type

Route tasks to appropriate models based on task characteristics.

## Routing Logic

```python
def select_model_for_task(task):
    title = task.get('title', '').lower()
    needs_code = any(kw in title for kw in [
        '修复', 'fix', '实现', 'implement', '代码', 'code',
        'uvisa', '前端', '后端', '恢复', '集成', 'refactor'
    ])
    
    if needs_code:
        return {
            'model': 'gpt-5.5',
            'provider': 'openai-codex',
            'max_turns': 30,
            'timeout': 600,
            'reason': 'code modification needs capable coding agent'
        }
    else:
        return {
            'model': 'mimo-v2.5-pro',
            'provider': 'xiaomi',
            'max_turns': 15,
            'timeout': 300,
            'reason': 'analysis/evaluation can use lighter model'
        }
```

## Integration Point

In `delegate_to_worker()`:
```python
routing = select_model_for_task(task)
cmd = [
    'hermes', 'chat', '-q', context,
    '--model', routing['model'], '--provider', routing['provider'],
    '--quiet', '--max-turns', str(routing['max_turns']),
    '--source', f'team-worker-{eid[:8]}',
    '--ignore-rules',
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=routing['timeout'])
```

## Why This Matters

- Code tasks need: file read/write, terminal, test execution, build verification
- Analysis tasks need: reasoning, comparison, recommendation
- Using MiMo for code tasks → insufficient capability → verification fails
- Using GPT-5.5 for analysis → overkill → wasted budget

## Extending the Router

Add more routing rules as patterns emerge:
```python
'security': {'model': 'claude-opus-4-7', 'max_turns': 20},  # careful review
'docs': {'model': 'mimo-v2.5-pro', 'max_turns': 10},  # lightweight
'research': {'model': 'deepseek-v4-pro', 'max_turns': 25},  # thorough analysis
```
