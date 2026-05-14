# DeepSeek-TUI Token Optimization Analysis

Source: https://github.com/Hmbown/DeepSeek-TUI (Rust, ~219K lines)

## Key Mechanisms

### 1. Tool Result Spilling (truncate.rs + recall_archive.rs)
- Results >4K tokens → V4-Flash synthesis sub-agent condenses to ≤800 words
- Raw content stored in WorkshopVariables.last_tool_result
- Model retrieves via retrieve_tool_result with modes: summary/head/tail/lines/query
- **Hermes port**: agent/result_spiller.py + token_compressor.py integration

### 2. var_handle Symbolic Reference (tools/handle.rs)
- ~200 byte JSON reference replaces large payloads in neural context
- Fields: kind, session_id, name, type_name, length, repr_preview (160 chars), sha256
- handle_read tool: slice/range/count/jsonpath projections, max_chars=12K default
- **Hermes port**: ResultSpiller stores to disk, returns hash+summary handle

### 3. RLM (Recursive Language Model) (rlm/)
- Persistent Python REPL keeps long inputs OUT of root model context
- "Symbolic state": data lives in REPL variables, model sees only metadata
- Bounded helpers: peek(), search(), chunk(), sub_query_batch()
- var_handle system: large returned values parked behind handles
- 5-phase: Load → Orient → Compute → Recurse → Converge

### 4. Large Output Router (tools/large_output_router.rs)
- Tool results >4,096 tokens intercepted before entering parent context
- V4-Flash synthesis sub-agent produces ≤800-word summary
- Raw stored in variable for selective retrieval

### 5. Dynamic Thinking Budget
- 5 levels: off/low/medium/high/max
- Auto-selection per task: lookup→off, tool interp→low, code gen→medium, debug→high
- "Think once, reference many times" — cache conclusions in inline summaries
- **Hermes port**: TaskRouter → reasoning_effort mapping

### 6. Prefix Cache Optimization
- V4 caches shared prefixes at 128-token granularity, ~90% cost discount
- System prompt split: STATIC (cacheable) + VOLATILE (per-turn)
- Working-set metadata injected into USER message, not system prompt
- Byte-identity tests ensure prefix stability

### 7. Locale Bookend Pattern
- Native-script reinforcement at BOTH ends of system prompt
- Opening anchors behavior; closing at max-recency position
- Prevents English code from drifting model's reasoning language
- **Hermes port**: persona.md + volatile layer Chinese anchor

## Constants
- MAX_RLM_ITERATIONS = 25
- MAX_BATCH = 16
- CHILD_TIMEOUT_SECS = 120
- ROOT_MAX_TOKENS = 4096
- STDOUT_METADATA_PREVIEW = 800 chars
- MAX_HISTORY_MESSAGES = 20
