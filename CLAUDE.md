## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Model pipeline (division of labor)

Route work across models instead of doing everything in this session. Two
subagents are defined in `.claude/agents/`; spawn them with the Agent tool using
the matching `subagent_type`.

1. **Scout — analyze & prepare the ground (Sonnet, read-only).** For any
   non-trivial code task, delegate to the `scout` agent first. It scopes the
   request the way graphify does and returns an implementation brief (exact file
   targets, data flow, constraints, test surface). Skip only for genuine
   one-liners or when you already hold full context.
2. **Build the code (Opus 4.8 — this session).** This is the only stage Opus
   does directly: take Scout's brief and write the actual implementation. Don't
   spend Opus on exploration Scout can do, or on tests/chores Worker can do.
3. **Tests & simple tasks (Sonnet).** After the core code exists, delegate
   test-writing and low-risk mechanical work (small refactors, renames,
   docstrings, config tweaks, lint fixes) to the `worker` agent, then review
   what it returns.

Both subagents already enforce the graphify-first rule and know the project's
`.venv` / pytest / ruff commands. To run the analysis stage cheaper/faster, set
`model: haiku` in `.claude/agents/scout.md`.
