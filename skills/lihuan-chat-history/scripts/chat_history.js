#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const os = require("os");

const HOME = os.homedir();

function usage() {
  console.log(`Usage:
  chat_history.js list [--source codex|claude|all] [--days N] [--limit N] [--json]
  chat_history.js search <query> [--source codex|claude|all] [--days N] [--limit N] [--context N] [--json]
  chat_history.js show <last|id|path> [--source codex|claude|all] [--tail N] [--json]
  chat_history.js stats [--source codex|claude|all] [--days N] [--limit N] [--json]
  chat_history.js tools <last|id|path> [--source codex|claude|all] [--json]

Defaults: source=all, limit=20, days=30, context=1, tail=30. Output is redacted.`);
}

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) {
      out._.push(a);
      continue;
    }
    const key = a.slice(2);
    if (key === "json") {
      out.json = true;
    } else if (key === "help") {
      out.help = true;
    } else {
      out[key] = argv[++i];
    }
  }
  return out;
}

function walk(dir, pred, acc = []) {
  if (!fs.existsSync(dir)) return acc;
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    let st;
    try {
      st = fs.statSync(p);
    } catch {
      continue;
    }
    if (st.isDirectory()) walk(p, pred, acc);
    else if (pred(p, st)) acc.push({ path: p, stat: st });
  }
  return acc;
}

function candidateFiles(source) {
  const sources = source === "all" ? ["codex", "claude"] : [source];
  const files = [];
  for (const s of sources) {
    if (s === "codex") {
      files.push(...walk(path.join(HOME, ".codex", "sessions"), p => p.endsWith(".jsonl")).map(x => ({ ...x, source: "codex" })));
    }
    if (s === "claude") {
      files.push(...walk(path.join(HOME, ".claude", "projects"), p => p.endsWith(".jsonl")).map(x => ({ ...x, source: "claude" })));
    }
  }
  return files.sort((a, b) => b.stat.mtimeMs - a.stat.mtimeMs);
}

function textFromContent(content) {
  if (!content) return "";
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.map(item => {
      if (typeof item === "string") return item;
      if (!item || typeof item !== "object") return "";
      return item.text || item.input_text || item.content || "";
    }).filter(Boolean).join("\n");
  }
  if (typeof content === "object") return content.text || content.input_text || JSON.stringify(content);
  return String(content);
}

function shouldSkipText(text) {
  const t = text.trim();
  if (!t) return true;
  return t.startsWith("<environment_context>") ||
    t.startsWith("<permissions instructions>") ||
    t.startsWith("<skills_instructions>") ||
    t.startsWith("<plugins_instructions>") ||
    t.includes("<local-command-caveat>") ||
    t.includes("<command-name>/clear</command-name>");
}

function redact(text) {
  return text
    .replace(/(https:\/\/open\.feishu\.cn\/open-apis\/bot\/v2\/hook\/)[A-Za-z0-9-]+/g, "$1[REDACTED]")
    .replace(/\b(sk-[A-Za-z0-9_-]{20,})\b/g, "[REDACTED_OPENAI_KEY]")
    .replace(/\b([A-Za-z0-9_-]{32,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})\b/g, "[REDACTED_TOKEN]")
    .replace(/(api[_-]?key|token|secret|password|passwd|pwd)(\s*[:=]\s*)[^\s"'`,;]+/gi, "$1$2[REDACTED]")
    .replace(/(Authorization:\s*Bearer\s+)[^\s"'`,;]+/gi, "$1[REDACTED]");
}

function safeSnippet(text, max = 260) {
  const cleaned = redact(text).replace(/\s+/g, " ").trim();
  return cleaned.length > max ? cleaned.slice(0, max - 1) + "..." : cleaned;
}

function readSession(file) {
  const meta = {
    source: file.source,
    path: file.path,
    id: path.basename(file.path, ".jsonl"),
    cwd: "",
    startedAt: null,
    updatedAt: new Date(file.stat.mtimeMs).toISOString(),
    sizeBytes: file.stat.size,
    messages: [],
    tools: {},
    parseErrors: 0,
  };

  const lines = fs.readFileSync(file.path, "utf8").split(/\r?\n/);
  for (const line of lines) {
    if (!line.trim()) continue;
    let obj;
    try {
      obj = JSON.parse(line);
    } catch {
      meta.parseErrors++;
      continue;
    }
    const ts = obj.timestamp || obj.created_at || obj.createdAt || obj?.payload?.timestamp || obj?.payload?.started_at || null;
    if (ts && !meta.startedAt) meta.startedAt = ts;

    if (file.source === "codex") {
      if (obj.type === "session_meta" && obj.payload) {
        meta.id = obj.payload.id || meta.id;
        meta.cwd = obj.payload.cwd || meta.cwd;
        meta.startedAt = obj.payload.timestamp || meta.startedAt;
      }
      const p = obj.payload || {};
      if (obj.type === "event_msg" && p.type === "user_message") {
        const text = textFromContent(p.message);
        if (!shouldSkipText(text)) meta.messages.push({ ts, role: "user", text });
      }
      if (obj.type === "response_item" && p.type === "message") {
        const role = p.role || "assistant";
        const text = textFromContent(p.content);
        if (!shouldSkipText(text)) meta.messages.push({ ts, role, text });
      }
      if (obj.type === "response_item" && (p.type === "function_call" || p.type === "tool_call")) {
        const name = p.name || p.tool_name || "tool";
        meta.tools[name] = (meta.tools[name] || 0) + 1;
      }
    } else if (file.source === "claude") {
      if (obj.cwd && !meta.cwd) meta.cwd = obj.cwd;
      if (obj.sessionId) meta.id = obj.sessionId;
      if (obj.isMeta) continue;
      if (obj.type === "user" || obj.type === "assistant") {
        const role = obj?.message?.role || obj.type;
        const text = textFromContent(obj?.message?.content);
        if (!shouldSkipText(text)) meta.messages.push({ ts: obj.timestamp || ts, role, text });
      }
      if (obj.type === "assistant") {
        const content = obj?.message?.content || [];
        if (Array.isArray(content)) {
          for (const part of content) {
            if (part && part.type === "tool_use") {
              const name = part.name || "tool";
              meta.tools[name] = (meta.tools[name] || 0) + 1;
            }
          }
        }
      }
    }
  }
  if (!meta.startedAt) meta.startedAt = new Date(file.stat.birthtimeMs || file.stat.mtimeMs).toISOString();
  return meta;
}

function filterByDays(files, days) {
  if (!days) return files;
  const cutoff = Date.now() - Number(days) * 24 * 60 * 60 * 1000;
  return files.filter(f => f.stat.mtimeMs >= cutoff);
}

function resolveSession(ref, opts) {
  const files = filterByDays(candidateFiles(opts.source), null);
  if (ref === "last") return files[0] && readSession(files[0]);
  if (fs.existsSync(ref)) {
    const source = ref.includes(`${path.sep}.claude${path.sep}`) ? "claude" : "codex";
    return readSession({ path: ref, source, stat: fs.statSync(ref) });
  }
  for (const f of files) {
    if (f.path.includes(ref) || path.basename(f.path, ".jsonl") === ref) return readSession(f);
  }
  return null;
}

function summarizeSession(s) {
  const firstUser = s.messages.find(m => m.role === "user");
  const lastAssistant = [...s.messages].reverse().find(m => m.role === "assistant");
  return {
    source: s.source,
    id: s.id,
    path: s.path,
    cwd: s.cwd,
    startedAt: s.startedAt,
    updatedAt: s.updatedAt,
    sizeKB: Math.round(s.sizeBytes / 1024),
    messageCount: s.messages.length,
    firstUser: firstUser ? safeSnippet(firstUser.text) : "",
    lastAssistant: lastAssistant ? safeSnippet(lastAssistant.text) : "",
  };
}

function printList(items, json) {
  if (json) return console.log(JSON.stringify(items, null, 2));
  for (const x of items) {
    console.log(`[${x.source}] ${x.id}`);
    console.log(`  time: ${x.startedAt || ""} -> ${x.updatedAt || ""}  size: ${x.sizeKB}KB  messages: ${x.messageCount}`);
    if (x.cwd) console.log(`  cwd: ${x.cwd}`);
    if (x.firstUser) console.log(`  first: ${x.firstUser}`);
    if (x.lastAssistant) console.log(`  last: ${x.lastAssistant}`);
  }
}

function cmdList(opts) {
  const files = filterByDays(candidateFiles(opts.source), opts.days).slice(0, Number(opts.limit));
  printList(files.map(readSession).map(summarizeSession), opts.json);
}

function cmdSearch(query, opts) {
  const q = query.toLowerCase();
  const context = Number(opts.context);
  const hits = [];
  for (const f of filterByDays(candidateFiles(opts.source), opts.days)) {
    const s = readSession(f);
    for (let i = 0; i < s.messages.length; i++) {
      const m = s.messages[i];
      if (!m.text.toLowerCase().includes(q)) continue;
      const around = s.messages.slice(Math.max(0, i - context), i + context + 1).map(x => ({
        role: x.role,
        text: safeSnippet(x.text, 360),
      }));
      hits.push({ ...summarizeSession(s), matchRole: m.role, match: safeSnippet(m.text, 420), context: around });
      if (hits.length >= Number(opts.limit)) break;
    }
    if (hits.length >= Number(opts.limit)) break;
  }
  if (opts.json) return console.log(JSON.stringify(hits, null, 2));
  for (const h of hits) {
    console.log(`[${h.source}] ${h.id}`);
    console.log(`  time: ${h.startedAt || ""}  cwd: ${h.cwd || ""}`);
    console.log(`  match(${h.matchRole}): ${h.match}`);
    for (const c of h.context) console.log(`    ${c.role}: ${c.text}`);
  }
}

function cmdShow(ref, opts) {
  const s = resolveSession(ref, opts);
  if (!s) {
    console.error(`No session found for: ${ref}`);
    process.exit(2);
  }
  const tail = Number(opts.tail);
  const messages = s.messages.slice(-tail).map(m => ({ ts: m.ts, role: m.role, text: redact(m.text) }));
  const out = { ...summarizeSession(s), messages };
  if (opts.json) return console.log(JSON.stringify(out, null, 2));
  console.log(`[${out.source}] ${out.id}`);
  console.log(`path: ${out.path}`);
  console.log(`cwd: ${out.cwd || ""}`);
  console.log(`time: ${out.startedAt || ""} -> ${out.updatedAt || ""}`);
  for (const m of messages) {
    console.log(`\n${m.role.toUpperCase()} ${m.ts || ""}`);
    console.log(m.text);
  }
}

function cmdStats(opts) {
  const rows = filterByDays(candidateFiles(opts.source), opts.days).slice(0, Number(opts.limit)).map(readSession).map(s => {
    const chars = s.messages.reduce((n, m) => n + m.text.length, 0);
    const toolCalls = Object.values(s.tools).reduce((a, b) => a + b, 0);
    return { ...summarizeSession(s), chars, approxTokens: Math.round(chars / 4), toolCalls };
  });
  if (opts.json) return console.log(JSON.stringify(rows, null, 2));
  for (const r of rows) {
    console.log(`[${r.source}] ${r.id} messages=${r.messageCount} approxTokens=${r.approxTokens} tools=${r.toolCalls} size=${r.sizeKB}KB`);
    if (r.cwd) console.log(`  ${r.cwd}`);
  }
}

function cmdTools(ref, opts) {
  const s = resolveSession(ref, opts);
  if (!s) {
    console.error(`No session found for: ${ref}`);
    process.exit(2);
  }
  const rows = Object.entries(s.tools).sort((a, b) => b[1] - a[1]).map(([tool, count]) => ({ tool, count }));
  const out = { ...summarizeSession(s), tools: rows };
  if (opts.json) return console.log(JSON.stringify(out, null, 2));
  console.log(`[${out.source}] ${out.id}`);
  if (!rows.length) console.log("No tool calls found or tool events were not recorded in this transcript.");
  for (const r of rows) console.log(`${r.tool}: ${r.count}`);
}

const args = parseArgs(process.argv.slice(2));
const cmd = args._[0];
const opts = {
  source: args.source || "all",
  days: args.days || "30",
  limit: args.limit || "20",
  context: args.context || "1",
  tail: args.tail || "30",
  json: Boolean(args.json),
};

if (!cmd || args.help) {
  usage();
  process.exit(args.help ? 0 : 1);
}
if (!["all", "codex", "claude"].includes(opts.source)) {
  console.error("--source must be codex, claude, or all");
  process.exit(2);
}

if (cmd === "list") cmdList(opts);
else if (cmd === "search") {
  const query = args._.slice(1).join(" ");
  if (!query) {
    console.error("search requires a query");
    process.exit(2);
  }
  cmdSearch(query, opts);
} else if (cmd === "show") {
  cmdShow(args._[1] || "last", opts);
} else if (cmd === "stats") {
  cmdStats(opts);
} else if (cmd === "tools") {
  cmdTools(args._[1] || "last", opts);
} else {
  usage();
  process.exit(2);
}
