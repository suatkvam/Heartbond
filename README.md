# GPU SLA Escrow (working title) — Monad Metropolis

On-chain escrow that pays a GPU provider or refunds a renter based on per-slot uptime
reports. Anyone can trigger settlement; finality is a fixed timeout. Uptime data comes
from team-held reporter keys (not trustless — see docs/PRD.md §10, §13).

| Doc | For |
|---|---|
| `docs/SPEC.md` | exact rules with IDs (build + tests) |
| `docs/PRD.md` | research, claims, risks |
| `docs/UI_HANDOFF.md` | frontend teammate (TR) |
| `docs/PLAN.md` | work order + day-0 checklist (TR) |
| `CLAUDE.md`, `.claude/agents/` | Claude Code setup |

```bash
pip install -r requirements.txt
pytest -q tests/                      # views pass, the rest go green as you implement
python scripts/smoke_test.py          # day-0 check on Monad Testnet (needs .env)
```
_The pitch-factchecker agent replaces this README before submission._
