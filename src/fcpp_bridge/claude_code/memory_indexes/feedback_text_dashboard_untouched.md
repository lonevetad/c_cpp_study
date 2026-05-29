---
name: feedback-text-dashboard-untouched
description: text_dashboard.py was deliberately skipped for the print→logging refactoring only; other refactorings are still allowed
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 30462d41-0a8b-4ed3-9933-02f384ad3e82
---

`src/fcpp_bridge/visualization/text_dashboard.py` was deliberately left unchanged during the print→logging refactoring pass (2026-05-28).

**Why:** Its `print(..., file=self._stream)` calls ARE the feature — the class is a stream-based text output component. The logging refactoring would have required per-instance child loggers, `setLevel` management, handler stacking guards, and `propagate` decisions; the user judged that too complex for a singular, contextualized case.

**How to apply:** If asked to continue or repeat the print→logging refactoring, skip `text_dashboard.py` and note it as a deliberate exception. For any OTHER future refactoring (API changes, type hints, OutputChannel integration, etc.) this file is fair game — do not treat it as permanently frozen.
