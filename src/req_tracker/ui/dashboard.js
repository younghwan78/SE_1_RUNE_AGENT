import {
  badge,
  displayStatus,
  el,
  emptyRow,
  escapeHtml,
  healthWarning,
  text,
} from "./core.js";
import { renderRunHealth, renderSourceHealth } from "./source_health.js";
import { renderWorkQueue } from "./work_queue.js";

export const renderDashboard = ({
  summary,
  workQueue,
  sourceHealth,
  runHealth,
  riskSummary,
  recentActivity,
  projection,
}) => {
  const counts = summary.counts || {};
  const lastRun = summary.last_run;
  text("dashboard-title", `${summary.project_key || "RUNE_CAM_ALPHA"} Dashboard`);
  text(
    "dashboard-subtitle",
    lastRun
      ? `${lastRun.run_type} ${lastRun.status}: ${lastRun.run_id}`
      : "No run evidence loaded",
  );
  text("metric-health", displayStatus(summary.traceability_health));
  text("metric-runs", lastRun ? lastRun.status : "none");
  text("metric-nodes", `${counts.total_nodes || 0}`);
  text("metric-edges", `${counts.approved_edges || 0}/${counts.pending_edges || 0}`);
  text("metric-approvals", counts.pending_approvals || 0);
  text("metric-high-findings", counts.high_findings || 0);
  text("metric-findings", counts.open_findings || 0);
  text("metric-gate", displayStatus(summary.eval_gate?.status));
  text("metric-schedule", summary.schedule?.enabled ? "on" : "off");
  document.querySelectorAll(".health-card").forEach((card) => {
    const value = card.querySelector("strong")?.textContent || "";
    card.classList.toggle("warning", healthWarning(value));
  });
  renderWorkQueue(workQueue);
  renderSourceHealth(sourceHealth);
  renderRunHealth(runHealth);
  renderRiskSnapshot(riskSummary);
  renderRecentActivity(recentActivity);
  renderGraphPreview(projection, counts);
};

export const renderRiskSnapshot = (payload) => {
  const risk = payload.risk_by_severity || {};
  const top = payload.top_findings || [];
  const criticalHigh = (risk.critical || 0) + (risk.high || 0);
  text("risk-label", `${criticalHigh} critical/high`);
  el("risk-bars").innerHTML = ["critical", "high", "medium", "low"]
    .map(
      (severity) => `
        <div class="risk-bar">
          <span>${severity}</span>
          <strong>${risk[severity] || 0}</strong>
        </div>
      `,
    )
    .join("");
  const list = el("dashboard-risk-findings");
  list.replaceChildren();
  if (!top.length) {
    list.append(emptyRow("No risk findings"));
    return;
  }
  top.slice(0, 5).forEach((finding) => {
    const row = document.createElement("li");
    row.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(finding.title)}</span>${badge(escapeHtml(finding.priority), healthWarning(finding.priority))}
      </div>
      <div class="item-meta">${escapeHtml(finding.summary)}</div>
    `;
    list.append(row);
  });
};

export const renderRecentActivity = (payload) => {
  const list = el("dashboard-activity");
  const items = payload.items || [];
  list.replaceChildren();
  text("activity-label", `${items.length} events`);
  if (!items.length) {
    list.append(emptyRow("No recent activity"));
    return;
  }
  items.slice(0, 6).forEach((activity) => {
    const row = document.createElement("li");
    row.innerHTML = `
      <div class="item-title">
        <span>${escapeHtml(activity.action)}</span>${badge(escapeHtml(activity.outcome), activity.outcome !== "succeeded")}
      </div>
      <div class="item-meta">${escapeHtml(activity.summary)}<br>${escapeHtml(activity.created_at)}</div>
    `;
    list.append(row);
  });
};

export const renderGraphPreview = (projection, counts) => {
  const groups = projection.groups || [];
  text(
    "graph-preview-label",
    `${counts.total_nodes || 0} nodes / ${counts.pending_edges || 0} pending`,
  );
  el("graph-preview").innerHTML = `
    <div class="preview-stat">
      <strong>${counts.orphan_nodes || 0}</strong>
      <span>orphan nodes</span>
    </div>
    <div class="preview-stat">
      <strong>${counts.approved_edges || 0}/${counts.pending_edges || 0}</strong>
      <span>approved/pending edges</span>
    </div>
    <div class="preview-groups">
      ${groups
        .slice(0, 6)
        .map((group) => `<span>${escapeHtml(group.label)}: ${group.count}</span>`)
        .join("")}
    </div>
  `;
};
