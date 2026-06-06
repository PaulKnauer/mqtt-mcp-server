# Story Execution Dependency Graph

```mermaid
flowchart LR
    S11[1.1 Project Foundation]
    S12[1.2 MQTT Adapter + Service]
    S13[1.3 MCP Tools]
    S14[1.4 Auth + Preflight + Bootstrap]
    S15[1.5 AGENTS.md + Quality Gates]

    S11 --> S12
    S12 --> S13
    S11 --> S14
    S14 --> S13
    S13 --> S15
    S12 --> S15
    S14 --> S15
```

## Execution Order

| Story | Depends On | Recommended Agent |
|---|---|---|
| 1.1 Project Foundation | None | dev |
| 1.2 MQTT Adapter + Service | 1.1 | dev |
| 1.4 Auth + Preflight + Bootstrap | 1.1 | dev |
| 1.3 MCP Tools | 1.2, 1.4 | dev |
| 1.5 AGENTS.md + Quality Gates | 1.3, 1.2, 1.4 | tech-writer |

## Key Dependencies

- Story 1.2 and 1.4 can run in parallel after 1.1 completes (different modules — adapters/services vs auth/config/bootstrap).
- Story 1.3 needs both 1.2 (adapter + service) and 1.4 (auth + bootstrap) to be complete.
- Story 1.5 is a capstone that depends on all other stories being complete.
