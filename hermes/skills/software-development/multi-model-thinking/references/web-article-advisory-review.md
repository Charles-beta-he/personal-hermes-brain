# Web article extraction and advisory multi-model review

Use this when a Cloudflare-protected or dynamic web article is relevant to multi-model architecture/adoption review.

## Fetching article text

1. Try normal web/browser access first.
2. If browser hits a Cloudflare challenge or `urllib`/curl gets 403, try Jina Reader:

```bash
python3 - <<'PY'
import urllib.request
url = 'https://r.jina.ai/http://r.jina.ai/http://https://example.com/article/path'
req = urllib.request.Request(url, headers={'User-Agent':'curl/8'})
with urllib.request.urlopen(req, timeout=60) as r:
    text = r.read().decode('utf-8', 'replace')
open('/tmp/article.md', 'w').write(text)
print(len(text))
PY
```

`https://r.jina.ai/http://r.jina.ai/http://https://...` worked for the OpenAI Symphony article after direct OpenAI access returned 403/Cloudflare. Do not treat this as authoritative if it truncates; preserve the source URL and extracted cache path.

## Packaging for multi-model review

- Extract specific article excerpts into evidence entries.
- Create explicit claims (`C1`, `C2`, ...) and link evidence with `supports`.
- Include local artifact evidence if the review also evaluates a landing implementation.
- If T3 discussion times out after all planners answer, inspect the tick and label the result `multi-view advisory` or `weak_consensus`, not full certification.

## Common interpretation pattern for orchestration articles

For external orchestration articles (e.g. Symphony): distinguish:
- transferable principles: task/deliverable control planes, task DAGs/dependencies, workflow contracts, persistent workpads/workspaces, review packets, host-side typed tool proxies;
- non-default adoption: second canonical tracker, heavyweight daemon/runtime, exposing tokens to subagents, unattended destructive execution.
