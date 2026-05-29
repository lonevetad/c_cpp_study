---
name: feedback-clarification-style
description: "How to handle ambiguous requests: ask questions AND always offer autonomous-decision option"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e0e1ffd8-f841-4b03-8663-5d988f484735
---

When a task has insufficiently specified or ambiguous parts, ask clarifying questions rather than silently assuming.

Always include **"No, go and take decisions autonomously after logging those decisions"** as one of the available options in any clarifying question. When the user selects this option (or says something equivalent), proceed using best judgment and document each significant decision made (what was chosen, why, what the alternatives were) in the response or a relevant log/journal file.

**Why:** User explicitly requested this option be available so they can opt into autonomous mode without having to repeat the instruction each time.

**How to apply:** Any `AskUserQuestion` call should include this as an option. When proceeding autonomously, log decisions inline in the response text (brief: decision + rationale) or in the relevant `.md` journal if the task warrants it.
