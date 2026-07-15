# P0 Cross-Session Recovery Evidence

Date: 2026-07-15
Result: PASS WITH INTERACTIVE MCP LIMIT

## Plugin

- Marketplace: `personal`
- Status: `installed, enabled`
- Version: `0.1.0+codex.20260715062128`
- Source: `/Users/lihuan/ai-workspace/plugins/codex-image-workbench`
- Workbench source: `/Users/lihuan/ai-workspace/codex-image-workbench`
- MCP stdio test: tool discovery and project/job/claim calls passed.

## Recovery Run

- Job: `job_01KXJ744852WJHZTHGNHQ23S0B`
- Origin worker: `p0-origin-session`
- Origin attempt: 1
- Origin lease: forced to expire
- Fresh Codex thread: `019f6474-60c4-7363-b48a-c9bc6511ab50`
- Recovery worker: `p0-fresh-codex-exec-shell`
- Recovery attempt: 2
- Final status: `failed`
- Final reason: `P0 cross-session handoff verified`

The second Codex process reclaimed the expired lease from the shared SQLite database and closed the test job without generating an image.

## MCP Approval Boundary

A separate fresh Codex thread, `019f6472-dbd6-7a63-b5ee-efc3a20c8fd5`, loaded the installed plugin and attempted `claim_generation_job` through MCP. Non-interactive `codex exec` cancelled the write-capable MCP tool because no user could approve it. No state was changed by those cancelled calls.

This confirms the supported automation level remains `interactive_resumable`: a live interactive Codex task can approve and use the MCP tools, while unattended non-interactive MCP writes are not claimed as supported.
