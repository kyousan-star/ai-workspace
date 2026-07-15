const state = {
  dashboard: null,
  projectId: null,
  project: null,
  selectedAssetId: null,
  uploadJobId: null,
  activeTab: "studio",
};

const el = (id) => document.getElementById(id);
const escapeHtml = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `Request failed: ${response.status}`);
  return body;
}

function toast(message) {
  const node = el("toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 3200);
}

function statusLabel(status) {
  return {
    queued: "待执行",
    leased: "运行中",
    awaiting_import: "待回导",
    succeeded: "已完成",
    failed: "失败",
    cancelled: "已取消",
    not_run: "未质检",
    needs_review: "待复核",
    passed: "通过",
    transient: "临时",
    candidate: "候选",
    approved: "已批准",
    published: "已上线",
    validated: "已验证",
    rejected: "已拒绝",
    retired: "已退役",
  }[status] || status;
}

function pill(status) {
  return `<span class="status-pill status-${escapeHtml(status)}">${escapeHtml(statusLabel(status))}</span>`;
}

function lines(value) {
  return String(value || "").split("\n").map((item) => item.trim()).filter(Boolean);
}

async function loadDashboard() {
  state.dashboard = await api("/api/dashboard");
  renderProjects();
  renderWorkerState();
  if (!state.projectId && state.dashboard.projects.length) {
    await selectProject(state.dashboard.projects[0].project_id);
  } else if (!state.dashboard.projects.length) {
    el("empty-view").classList.remove("hidden");
    el("project-view").classList.add("hidden");
  }
}

function renderProjects() {
  const projects = state.dashboard?.projects || [];
  el("project-count").textContent = projects.length;
  el("project-list").innerHTML = projects.map((project) => `
    <button class="project-item ${project.project_id === state.projectId ? "active" : ""}" data-project-id="${escapeHtml(project.project_id)}" type="button">
      <strong>${escapeHtml(project.name)}</strong>
      <small>${escapeHtml(project.brand)} · ${escapeHtml(project.sku)} · ${escapeHtml(project.marketplace)}</small>
      <b>${project.open_job_count || 0}</b>
    </button>
  `).join("");
  document.querySelectorAll("[data-project-id]").forEach((button) => {
    button.addEventListener("click", () => selectProject(button.dataset.projectId));
  });
}

function renderWorkerState() {
  const counts = state.dashboard?.counts || {};
  const node = el("worker-state");
  node.className = "worker-state";
  if (state.project?.jobs?.some((job) => job.execution_status === "leased")) {
    node.classList.add("running");
    node.innerHTML = "<i></i>Worker 运行中";
  } else if ((counts.queued_jobs || 0) > 0) {
    node.classList.add("waiting");
    node.innerHTML = `<i></i>${counts.queued_jobs} 个任务待领取`;
  } else {
    node.innerHTML = "<i></i>空闲";
  }
}

async function selectProject(projectId) {
  state.projectId = projectId;
  state.project = await api(`/api/projects/${encodeURIComponent(projectId)}`);
  state.selectedAssetId = null;
  renderProjects();
  renderProject();
  renderInspector();
  renderWorkerState();
}

function renderProject() {
  const { project, jobs, assets } = state.project;
  el("empty-view").classList.add("hidden");
  el("project-view").classList.remove("hidden");
  el("project-title").textContent = project.name;
  el("project-kicker").textContent = `${project.project_mode === "launch" ? "新品" : "在售优化"} · ${project.brand} · ${project.sku} · Amazon ${project.marketplace}`;
  el("stat-jobs").textContent = jobs.length;
  el("stat-open").textContent = jobs.filter((job) => ["queued", "leased", "awaiting_import"].includes(job.execution_status)).length;
  el("stat-assets").textContent = assets.length;
  el("stat-qc").textContent = assets.filter((asset) => ["not_run", "needs_review"].includes(asset.qc_status)).length;
  renderJobs();
  renderAssets();
  renderQuality();
  fillParentOptions();
}

function renderJobs() {
  const jobs = state.project.jobs;
  el("queue-summary").textContent = `${jobs.length} 个任务`;
  el("jobs-body").innerHTML = jobs.length ? jobs.map((job) => {
    const prompt = job.contract?.prompt || "";
    const mode = job.execution_mode === "codex_auto" ? "Codex" : "手动";
    const asset = state.project.assets.find((item) => item.job_id === job.job_id);
    let actions = "";
    if (job.execution_status === "queued") {
      actions = `<button class="mini-button" data-copy-worker="${escapeHtml(job.job_id)}" type="button">复制 Worker</button>`;
    } else if (job.execution_status === "awaiting_import") {
      actions = `<button class="mini-button" data-export-job="${escapeHtml(job.job_id)}" type="button">导出</button><button class="mini-button" data-import-job="${escapeHtml(job.job_id)}" type="button">回导</button>`;
    } else if (asset) {
      actions = `<button class="mini-button" data-view-asset="${escapeHtml(asset.asset_id)}" type="button">查看</button>`;
    }
    return `<tr>
      <td><strong>${escapeHtml(job.slot_key || job.contract?.slot)}</strong></td>
      <td class="prompt-cell" title="${escapeHtml(prompt)}">${escapeHtml(job.operation === "edit" ? "编辑 · " : "生成 · ")}${escapeHtml(prompt)}</td>
      <td>${mode}</td>
      <td>${pill(job.execution_status)}</td>
      <td>${job.attempts}/${job.max_attempts}</td>
      <td><div class="row-actions">${actions}</div></td>
    </tr>`;
  }).join("") : `<tr><td colspan="6">暂无任务</td></tr>`;

  document.querySelectorAll("[data-copy-worker]").forEach((button) => button.addEventListener("click", async () => {
    const command = `cd /Users/lihuan/ai-workspace/codex-image-workbench && python3 -m workbench.cli claim --worker codex-workbench`;
    await navigator.clipboard.writeText(command);
    toast("Worker 命令已复制");
  }));
  document.querySelectorAll("[data-export-job]").forEach((button) => button.addEventListener("click", () => exportJob(button.dataset.exportJob)));
  document.querySelectorAll("[data-import-job]").forEach((button) => button.addEventListener("click", () => chooseImport(button.dataset.importJob)));
  document.querySelectorAll("[data-view-asset]").forEach((button) => button.addEventListener("click", () => selectAsset(button.dataset.viewAsset)));
}

function renderAssets() {
  const assets = state.project.assets;
  el("asset-summary").textContent = `${assets.length} 个版本`;
  el("asset-grid").innerHTML = assets.length ? assets.map((asset) => `
    <button class="asset-card ${asset.asset_id === state.selectedAssetId ? "selected" : ""}" data-asset-id="${escapeHtml(asset.asset_id)}" type="button">
      <img src="/api/assets/${encodeURIComponent(asset.asset_id)}/media" alt="${escapeHtml(asset.slot_key)} 结果图" loading="lazy" />
      <span class="asset-card-body">
        <span class="asset-card-title"><span>${escapeHtml(asset.slot_key)}</span><span>${asset.width || "?"}×${asset.height || "?"}</span></span>
        <span class="asset-statuses">${pill(asset.technical_status)}${pill(asset.qc_status)}${pill(asset.registry_status)}</span>
        <span class="asset-meta"><span>${asset.source_type === "codex_auto" ? "Codex" : "手动"}</span><span>${asset.parent_asset_id ? "子版本" : "根版本"}</span></span>
      </span>
    </button>
  `).join("") : `<div class="inspector-empty">暂无结果</div>`;
  document.querySelectorAll("[data-asset-id]").forEach((button) => button.addEventListener("click", () => selectAsset(button.dataset.assetId)));
}

function renderQuality() {
  const assets = state.project.assets;
  el("quality-list").innerHTML = assets.length ? assets.map((asset) => `
    <button class="quality-row" data-quality-asset="${escapeHtml(asset.asset_id)}" type="button">
      <img src="/api/assets/${encodeURIComponent(asset.asset_id)}/media" alt="${escapeHtml(asset.slot_key)}" loading="lazy" />
      <span><strong>${escapeHtml(asset.slot_key)} · ${escapeHtml(asset.asset_id)}</strong><small>${asset.width || "?"} × ${asset.height || "?"} · ${escapeHtml(asset.file_format || "unknown")}</small></span>
      ${pill(asset.technical_status)}
      ${pill(asset.qc_status)}
    </button>
  `).join("") : `<div class="inspector-empty">暂无待检结果</div>`;
  document.querySelectorAll("[data-quality-asset]").forEach((button) => button.addEventListener("click", () => selectAsset(button.dataset.qualityAsset)));
}

async function selectAsset(assetId) {
  state.selectedAssetId = assetId;
  const asset = await api(`/api/assets/${encodeURIComponent(assetId)}`);
  renderAssets();
  renderInspector(asset);
  el("inspector").classList.add("open");
}

function renderInspector(asset = null) {
  const inspector = el("inspector");
  if (!asset) {
    inspector.innerHTML = `<div class="inspector-empty">选择一张结果图</div>`;
    inspector.classList.remove("open");
    return;
  }
  const checks = asset.technical_checks?.checks || [];
  const canRegister = asset.technical_status === "passed" && asset.qc_status === "passed" && asset.registry_status === "transient";
  inspector.innerHTML = `
    <div class="inspector-content">
      <img class="inspector-image" src="/api/assets/${encodeURIComponent(asset.asset_id)}/media" alt="选中结果" />
      <section class="inspector-section">
        <div class="inspector-title"><strong>${escapeHtml(asset.asset_id)}</strong><button id="close-inspector" class="icon-button" type="button" aria-label="关闭">×</button></div>
      </section>
      <section class="inspector-section">
        <h3>版本</h3>
        <dl class="detail-list">
          <dt>图位</dt><dd>${escapeHtml(asset.slot_key)}</dd>
          <dt>父版本</dt><dd>${escapeHtml(asset.parent_asset_id || "根版本")}</dd>
          <dt>来源</dt><dd>${escapeHtml(asset.source_type)}</dd>
          <dt>文件</dt><dd>${asset.width || "?"} × ${asset.height || "?"} ${escapeHtml(asset.file_format || "")}</dd>
          <dt>SHA-256</dt><dd>${escapeHtml(asset.sha256.slice(0, 16))}…</dd>
        </dl>
      </section>
      <section class="inspector-section">
        <h3>技术检查 ${pill(asset.technical_status)}</h3>
        <div class="check-list">${checks.length ? checks.map((check) => `<div class="check-item"><span>${escapeHtml(check.name)}</span><b class="${check.passed ? "ok" : "bad"}">${check.passed ? "通过" : `${escapeHtml(check.actual)} / ${escapeHtml(check.expected)}`}</b></div>`).join("") : "<small>无检查项</small>"}</div>
      </section>
      <section class="inspector-section">
        <h3>人工 QC ${pill(asset.qc_status)}</h3>
        <div class="qc-controls">
          <textarea id="qc-notes" placeholder="记录产品、Claim、构图或可读性问题"></textarea>
          <div class="qc-buttons"><button class="danger-button" id="qc-fail" type="button">不通过</button><button class="primary-button" id="qc-pass" type="button" ${asset.technical_status !== "passed" ? "disabled" : ""}>通过</button></div>
        </div>
      </section>
      <section class="inspector-section">
        <h3>资产状态 ${pill(asset.registry_status)}</h3>
        <button id="candidate-button" class="secondary-button" type="button" ${canRegister ? "" : "disabled"}>登记为候选</button>
      </section>
    </div>`;
  el("close-inspector").addEventListener("click", () => renderInspector());
  el("qc-pass").addEventListener("click", () => evaluateSelected("passed"));
  el("qc-fail").addEventListener("click", () => evaluateSelected("failed"));
  el("candidate-button").addEventListener("click", registerCandidate);
}

async function evaluateSelected(status) {
  const notes = el("qc-notes").value.trim();
  await api(`/api/assets/${encodeURIComponent(state.selectedAssetId)}/evaluation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, notes }),
  });
  toast(status === "passed" ? "QC 已通过" : "已标记不通过");
  await refreshProject(state.selectedAssetId);
}

async function registerCandidate() {
  await api(`/api/assets/${encodeURIComponent(state.selectedAssetId)}/candidate`, { method: "POST" });
  toast("已登记为 candidate");
  await refreshProject(state.selectedAssetId);
}

async function refreshProject(selectedAssetId = state.selectedAssetId) {
  if (!state.projectId) return;
  state.project = await api(`/api/projects/${encodeURIComponent(state.projectId)}`);
  state.selectedAssetId = selectedAssetId;
  renderProject();
  renderWorkerState();
  if (selectedAssetId) {
    const asset = await api(`/api/assets/${encodeURIComponent(selectedAssetId)}`);
    renderInspector(asset);
  }
  state.dashboard = await api("/api/dashboard");
  renderProjects();
}

async function exportJob(jobId) {
  const result = await api(`/api/jobs/${encodeURIComponent(jobId)}/export`, { method: "POST" });
  await navigator.clipboard.writeText(result.package);
  toast("生成包路径已复制");
}

function chooseImport(jobId) {
  state.uploadJobId = jobId;
  el("file-input").value = "";
  el("file-input").click();
}

async function uploadResult(file) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(state.uploadJobId)}/import?filename=${encodeURIComponent(file.name)}`, {
    method: "POST",
    headers: { "Content-Type": file.type || "application/octet-stream" },
    body: file,
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "回导失败");
  toast(body.technical_status === "passed" ? "结果已回导，技术检查通过" : "结果已回导，技术检查未通过");
  await refreshProject(body.asset_id);
}

function fillParentOptions() {
  const options = state.project?.assets || [];
  el("parent-select").innerHTML = `<option value="">无</option>${options.map((asset) => `<option value="${escapeHtml(asset.asset_id)}">${escapeHtml(asset.slot_key)} · ${escapeHtml(asset.asset_id.slice(-10))}</option>`).join("")}`;
}

function openDialog(dialog) {
  dialog.showModal();
}

function closeDialog(button) {
  button.closest("dialog").close();
}

el("new-project-button").addEventListener("click", () => openDialog(el("project-dialog")));
document.querySelectorAll("[data-open-project]").forEach((button) => button.addEventListener("click", () => openDialog(el("project-dialog"))));
el("new-job-button").addEventListener("click", () => openDialog(el("job-dialog")));
document.querySelectorAll("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => closeDialog(button)));
el("refresh-button").addEventListener("click", async () => {
  await loadDashboard();
  if (state.projectId) await refreshProject();
  toast("已刷新");
});

el("project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const project = await api("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(form.entries())),
    });
    event.currentTarget.reset();
    el("project-dialog").close();
    await loadDashboard();
    await selectProject(project.project.project_id);
    toast("项目已创建");
  } catch (error) { toast(error.message); }
});

el("job-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const parentAssetId = form.get("parent_asset_id") || null;
  const parentAsset = state.project.assets.find((asset) => asset.asset_id === parentAssetId);
  const payload = {
    slot_key: form.get("slot_key"),
    operation: form.get("operation"),
    parent_asset_id: parentAssetId,
    execution_mode: form.get("execution_mode"),
    prompt: form.get("prompt"),
    invariants: lines(form.get("invariants")),
    avoid: lines(form.get("avoid")),
    acceptance: lines(form.get("acceptance")),
    references: parentAsset ? [{ path: parentAsset.source_path, role: "edit-target" }] : [],
    expected_output: { format: "png", aspect_ratio: "1:1" },
  };
  try {
    const result = await api(`/api/projects/${encodeURIComponent(state.projectId)}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    event.currentTarget.reset();
    el("job-dialog").close();
    await refreshProject();
    toast(result.created ? "任务已创建" : "相同任务已存在");
  } catch (error) { toast(error.message); }
});

el("operation-select").addEventListener("change", (event) => {
  const edit = event.target.value === "edit";
  el("parent-select").required = edit;
  if (!edit) el("parent-select").value = "";
});

el("file-input").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  try { await uploadResult(file); } catch (error) { toast(error.message); }
});

document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
  state.activeTab = button.dataset.tab;
  document.querySelectorAll("[data-tab]").forEach((item) => item.classList.toggle("active", item === button));
  el("studio-panel").classList.toggle("hidden", state.activeTab !== "studio");
  el("quality-panel").classList.toggle("hidden", state.activeTab !== "quality");
}));

loadDashboard().catch((error) => toast(error.message));
setInterval(() => {
  if (document.visibilityState !== "visible" || document.querySelector("dialog[open]")) return;
  if (state.projectId) refreshProject().catch(() => {});
}, 120000);
