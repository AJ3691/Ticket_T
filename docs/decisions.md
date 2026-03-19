
# Decision Log

Minimal, actionable tradeoffs for engineering alignment.

| #   | Decision                                     | Alternatives                             | Tradeoffs (+ / -)                                                                                                                                            |
| --- | -------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Keyword rules over LLM                       | LLM, embeddings                          | + deterministic, fast (<1ms), no cost<br>- low semantic accuracy, manual rules                                                                               |
| 2   | Strategy pattern (TriageStrategy)            | Inline logic in engine                   | + modular, swappable algorithms<br>- extra abstraction layer                                                                                                 |
| 3   | Pydantic validation                          | Manual if/else checks                    | + automatic 422 errors, schema docs<br>- less custom control                                                                                                 |
| 4   | File ownership (agents)                      | Git branches per agent                   | + zero merge conflicts, parallel-safe<br>- enforced by convention only                                                                                       |
| 5   | Frozen contracts before parallel work        | Dynamic contract evolution               | + prevents interface drift<br>- upfront coordination step                                                                                                    |
| 6   | In-memory telemetry                          | Prometheus, StatsD                       | + zero dependency, simple<br>- no persistence, not scalable                                                                                                  |
| 7   | Stateless design (no shared runtime state)   | Shared cache/memory                      | + scalable, concurrency-safe<br>- recomputation cost                                                                                                         |
| 8   | Scripted concurrent agents (non-interactive) | Manual terminals                         | + repeatable, automated, parallel execution<br>+ no human coordination needed<br>- no mid-execution control<br>- failures may propagate without intervention |
| 9   | Agents Direct file writes (current)          | Patch-based concurrency (isolated diffs) | + simple, fast, low setup<br>- risk of race conditions at scale (imports, shared files)<br>- harder to audit or rollback                                     |
# Why it fits / when it breaks

| #   | Decision                                   | Why it fits                                                          | When it breaks                                                                 |
| --- | ------------------------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1   | Keyword rules over LLM                     | Spec requires deterministic ranking and no external dependency       | Large domain complexity → move to hybrid (rules + embeddings)                  |
| 2   | Strategy pattern (TriageStrategy)          | Allows changing ranking logic without touching API/engine            | Overengineering if only 1 strategy forever                                     |
| 3   | Pydantic validation                        | Keeps API thin and consistent                                        | Complex validation rules → need custom validators                              |
| 4   | File ownership (agents)                    | Enables true concurrent agents without coordination overhead         | Larger teams → need stricter enforcement/tooling                               |
| 5   | Frozen contracts before parallel work      | Guarantees API + Core integrate cleanly                              | Rapid prototyping → slows iteration speed                                      |
| 6   | In-memory telemetry                        | Meets minimal telemetry requirement with lowest complexity           | Multi-instance / production → need external metrics system                     |
| 7   | Sequential test phase                      | Avoids writing tests on unstable interfaces                          | Large systems → need parallel CI validation                                    |
| 8   | Stateless design (no shared runtime state) | Matches agent architecture + API design                              | High traffic → introduce caching (Redis)                                       |
| 9   | Latency over accuracy                      | Prioritizes reliability and speed for MVP                            | Need higher quality → move to ML/LLM                                           |
| 10  | Scripted concurrent agents (non-interactiv | Enables deterministic agent orchestration and reproducibility        | Complex tasks or ambiguous failures → need interactive or supervised execution |
| 11  | Direct file writes (curren                 | Works well for small, controlled projects with strict file ownership | Breaks at scale or with shared dependencies                                    |
