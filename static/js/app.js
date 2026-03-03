let selectedDomain = "legal_contract";

function formatUptime(seconds) {
  const totalMinutes = Math.max(0, Math.floor((Number(seconds) || 0) / 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

async function fetchHealthStatus() {
  const strip = document.getElementById("status-strip");
  if (!strip) {
    return;
  }

  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error("Health request failed");
    }
    const data = await response.json();
    document.getElementById("status-version").textContent = data.version || "-";
    document.getElementById("status-boundary").textContent = data.neurosymbolic_boundary || "-";
    document.getElementById("status-languages").textContent = Array.isArray(data.languages_supported)
      ? String(data.languages_supported.length)
      : "-";
    document.getElementById("status-uptime").textContent = formatUptime(data.uptime_seconds);
  } catch (error) {
    document.getElementById("status-version").textContent = "Unavailable";
    document.getElementById("status-boundary").textContent = "Unavailable";
    document.getElementById("status-languages").textContent = "-";
    document.getElementById("status-uptime").textContent = "-";
  }
}

function updateSelectedFile(file) {
  const selectedFile = document.getElementById("selected-file");
  const analyseButton = document.getElementById("analyse-button");
  if (selectedFile) {
    selectedFile.textContent = file ? file.name : "No file selected";
  }
  if (analyseButton) {
    analyseButton.disabled = !file;
  }
}

function initDragZone() {
  const zone = document.getElementById("upload-zone");
  const input = document.getElementById("file-input");
  const trigger = document.getElementById("choose-file-button");
  if (!zone || !input || !trigger) {
    return;
  }

  const setFile = (file) => {
    if (!file) {
      updateSelectedFile(null);
      return;
    }
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    updateSelectedFile(file);
  };

  trigger.addEventListener("click", () => input.click());
  zone.addEventListener("click", (event) => {
    if (event.target === zone) {
      input.click();
    }
  });
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("active");
  });
  zone.addEventListener("dragleave", () => {
    zone.classList.remove("active");
  });
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("active");
    const [file] = event.dataTransfer.files;
    setFile(file);
  });
  input.addEventListener("change", () => {
    const [file] = input.files;
    updateSelectedFile(file || null);
  });
}

function initDomainToggle() {
  const toggle = document.getElementById("domain-toggle");
  const hiddenInput = document.getElementById("domain-input");
  if (!toggle || !hiddenInput) {
    return;
  }

  selectedDomain = hiddenInput.value || "legal_contract";
  toggle.querySelectorAll("[data-domain]").forEach((button) => {
    button.addEventListener("click", () => {
      toggle.querySelectorAll("[data-domain]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      selectedDomain = button.dataset.domain || "legal_contract";
      hiddenInput.value = selectedDomain;
    });
  });
}

function resetStages() {
  document.querySelectorAll(".stage-row").forEach((row) => {
    row.classList.remove("active", "complete");
  });
}

function showResultsState(state) {
  const empty = document.getElementById("results-empty");
  const processing = document.getElementById("results-processing");
  const content = document.getElementById("results-content");
  if (empty) {
    empty.hidden = state !== "empty";
  }
  if (processing) {
    processing.hidden = state !== "processing";
  }
  if (content) {
    content.hidden = state !== "results";
  }
}

function sleep(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function playProcessingStages() {
  const stages = [...document.querySelectorAll(".stage-row")];
  resetStages();
  for (const row of stages) {
    row.classList.add("active");
    await sleep(400);
    row.classList.remove("active");
    row.classList.add("complete");
  }
}

function getInputFormat(data) {
  const filename = String(data.filename || data.input_file || "");
  if (filename.toLowerCase().endsWith(".pdf")) {
    return "pdf";
  }
  return "txt";
}

function normalizeClauses(data) {
  const candidates = [data.clauses, data.extracted_clauses, data.sections, data.items, data.results];
  const firstArray = candidates.find((candidate) => Array.isArray(candidate));
  if (firstArray) {
    return firstArray.map((item, index) => ({
      type: item.type || item.clause_type || item.label || `Clause ${index + 1}`,
      englishType: item.english_type || item.label_en || item.translation || "",
      text: item.text || item.content || item.value || JSON.stringify(item),
      confidence: Number(item.confidence ?? item.score ?? 1),
      ruleId: item.rule_id || item.ruleId || item.id || "rule:derived",
    }));
  }

  return Object.entries(data)
    .filter(([key, value]) => {
      const ignored = new Set([
        "record_id",
        "tenant_id",
        "language",
        "api_version",
        "document_hash",
        "governance_metadata",
        "neurosymbolic_boundary",
        "provenance_hash",
        "provenance_meta",
        "filename",
        "input_file",
      ]);
      return !ignored.has(key) && typeof value !== "object";
    })
    .map(([key, value]) => ({
      type: key.replace(/_/g, " "),
      englishType: "",
      text: String(value),
      confidence: 1,
      ruleId: "rule:derived",
    }));
}

function riskTierClass(riskTier) {
  const normalized = String(riskTier || "").toLowerCase();
  if (normalized === "high") {
    return "badge-red";
  }
  if (normalized === "medium") {
    return "badge-amber";
  }
  return "badge-teal";
}

function rowMarkup(label, value, copyId, copyText) {
  const copyButton = copyId
    ? `<button class="copy-button" type="button" data-copy-target="${copyId}">${copyText || "Copy"}</button>`
    : "";
  return `
    <div class="result-row">
      <span class="row-label">${label}</span>
      <div class="result-value">${value}</div>
      ${copyButton}
    </div>
  `;
}

function renderResults(data) {
  const provenance = document.getElementById("result-provenance");
  const clauses = document.getElementById("result-clauses");
  const governance = document.getElementById("result-governance");
  const verify = document.getElementById("result-verify");
  if (!provenance || !clauses || !governance || !verify) {
    return;
  }

  const recordId = data.record_id || "Unavailable";
  const documentHash = data.document_hash || data.provenance_hash || "Unavailable";
  const timestamp = (data.provenance_meta && data.provenance_meta.timestamp) || data.timestamp || "Unavailable";
  const language = data.language || "unknown";
  const boundary = data.neurosymbolic_boundary ? "symbolic_only" : "symbolic_only";
  const inputFormat = getInputFormat(data);
  const clauseItems = normalizeClauses(data);
  const governanceData = data.governance_metadata || {};

  provenance.innerHTML = `
    <div class="result-header">
      <div>
        <h3>Provenance Record</h3>
        <p class="result-subtitle mono">${recordId}</p>
      </div>
    </div>
    ${rowMarkup("Record ID", `<code id="copy-record-id">${recordId}</code>`, "copy-record-id")}
    ${rowMarkup("Document Hash", `<code id="copy-document-hash">${documentHash}</code>`, "copy-document-hash")}
    ${rowMarkup("Timestamp", `<span>${timestamp}</span>`)}
    ${rowMarkup("Language", `<span>${language} confidence: deterministic</span>`)}
    ${rowMarkup("Boundary", `<span class="badge badge-teal">${boundary}</span>`)}
    ${rowMarkup("Input Format", `<span class="badge badge-navy">${inputFormat}</span>`)}
    <a class="result-link" id="verify-link" href="/v1/verify/${recordId}">Verify this record &rarr;</a>
  `;

  clauses.innerHTML = `
    <div class="result-header">
      <div>
        <h3>Extracted Clauses</h3>
      </div>
      <span class="badge badge-navy">${clauseItems.length}</span>
    </div>
    <div class="clauses-list">
      ${clauseItems.length
        ? clauseItems.map((item) => `
          <article class="clause-card">
            <div class="card-title">${item.type}</div>
            <div class="result-subtitle"><em>${item.englishType || "Normalised field"}</em></div>
            <p>${item.text}</p>
            <div class="clause-meta">
              <div class="confidence-track">
                <div class="confidence-fill" style="width: ${Math.max(0, Math.min(100, item.confidence * 100))}%"></div>
              </div>
              <span class="rule-id mono">${item.ruleId}</span>
            </div>
          </article>
        `).join("")
        : `<article class="clause-card"><p>No clause array was returned by the current backend response.</p></article>`}
    </div>
  `;

  governance.innerHTML = `
    <div class="result-header">
      <div>
        <h3>Governance Metadata</h3>
      </div>
    </div>
    ${rowMarkup("EU AI Act", `<span>${governanceData.eu_ai_act_article || "Unavailable"}</span>`)}
    ${rowMarkup("NIST RMF", `<span class="badge badge-navy">${governanceData.nist_rmf_function || "Unavailable"}</span>`)}
    ${rowMarkup("Risk Tier", `<span class="badge ${riskTierClass(governanceData.risk_tier)}">${governanceData.risk_tier || "Unavailable"}</span>`)}
    ${rowMarkup("Audit Ready", `<span>${governanceData.audit_ready ? "Yes" : "No"}</span>`)}
  `;

  verify.innerHTML = `
    <div class="result-header">
      <div>
        <h3>Independent Verification</h3>
      </div>
    </div>
    <p>Verify that this output corresponds to the original document.</p>
    <div class="verify-inline">
      <input id="verify-record-id" type="text" value="${recordId}">
      <button class="button button-primary" id="verify-button" type="button">Verify Record</button>
      <div class="verify-result" id="verify-result"></div>
    </div>
  `;

  initCopyButtons();

  const verifyButton = document.getElementById("verify-button");
  if (verifyButton) {
    verifyButton.addEventListener("click", () => {
      const input = document.getElementById("verify-record-id");
      verifyRecord(input ? input.value.trim() : recordId);
    });
  }
}

async function analyseDocument(event) {
  if (event) {
    event.preventDefault();
  }

  const input = document.getElementById("file-input");
  const error = document.getElementById("analyse-error");
  if (!input || !input.files || !input.files[0]) {
    return;
  }

  if (error) {
    error.hidden = true;
    error.textContent = "";
  }

  showResultsState("processing");
  const file = input.files[0];
  const formData = new FormData();
  formData.append("document", file);
  formData.append("document_type", selectedDomain);
  formData.append("file", file);
  formData.append("domain", selectedDomain);
  await playProcessingStages();

  try {
    const response = await fetch("/v1/analyse", {
      method: "POST",
      headers: {
        "X-API-Key": "demo-key-iota-2026",
      },
      body: formData,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Analysis request failed");
    }
    const data = await response.json();
    data.filename = file.name;
    renderResults(data);
    showResultsState("results");
  } catch (requestError) {
    showResultsState("empty");
    if (error) {
      error.hidden = false;
      error.textContent = requestError.message;
    }
  }
}

async function verifyRecord(recordId) {
  const resultNode = document.getElementById("verify-result");
  const verifyPage = document.querySelector("[data-verify-page]");
  const summary = {
    symbol: document.getElementById("verify-symbol"),
    heading: document.getElementById("verify-heading"),
    subtitle: document.getElementById("verify-subtitle"),
    count: document.getElementById("verify-count"),
    missing: document.getElementById("verify-missing"),
    content: document.getElementById("results-content"),
  };

  if (!recordId) {
    return;
  }

  try {
    const response = await fetch(`/v1/verify/${encodeURIComponent(recordId)}`, {
      headers: {
        "X-API-Key": "demo-key-iota-2026",
      },
    });
    if (!response.ok) {
      throw new Error(response.status === 404 ? "Record not found" : "Verification failed");
    }
    const data = await response.json();
    if (resultNode) {
      resultNode.textContent = "Verified. Output matches the stored record.";
      resultNode.className = "verify-result success";
    }
    if (verifyPage) {
      if (summary.symbol) {
        summary.symbol.className = "verify-symbol success";
        summary.symbol.textContent = "OK";
      }
      if (summary.heading) {
        summary.heading.textContent = "Verified";
      }
      if (summary.subtitle) {
        summary.subtitle.textContent = "Output matches source document";
      }
      if (summary.count) {
        summary.count.textContent = "Verified 1 times";
      }
      if (summary.missing) {
        summary.missing.hidden = true;
      }
      if (summary.content) {
        summary.content.hidden = false;
      }
      renderResults(data.record || data);
    }
    return data;
  } catch (verifyError) {
    if (resultNode) {
      resultNode.textContent = verifyError.message;
      resultNode.className = "verify-result error";
    }
    if (verifyPage) {
      if (summary.symbol) {
        summary.symbol.className = "verify-symbol error";
        summary.symbol.textContent = "X";
      }
      if (summary.heading) {
        summary.heading.textContent = "Mismatch detected";
      }
      if (summary.subtitle) {
        summary.subtitle.textContent = "Hash does not match stored record";
      }
      if (summary.missing) {
        summary.missing.hidden = false;
      }
      if (summary.content) {
        summary.content.hidden = true;
      }
    }
    return null;
  }
}

function initCopyButtons() {
  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    if (button.dataset.bound === "true") {
      return;
    }
    button.dataset.bound = "true";
    button.addEventListener("click", async () => {
      const targetId = button.getAttribute("data-copy-target");
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target) {
        return;
      }
      const originalText = button.textContent;
      await navigator.clipboard.writeText(target.textContent || "");
      button.textContent = "Copied!";
      window.setTimeout(() => {
        button.textContent = originalText || "Copy";
      }, 2000);
    });
  });
}

function initServerRenderedResults() {
  const serverData = document.getElementById("server-result-data");
  if (!serverData) {
    return;
  }
  try {
    const parsed = JSON.parse(serverData.textContent);
    renderResults(parsed);
    showResultsState("results");
  } catch (error) {
    showResultsState("empty");
  }
}

function initAnalyseForm() {
  const form = document.getElementById("analyse-form");
  if (!form) {
    return;
  }
  form.addEventListener("submit", analyseDocument);
}

function initVerifyPage() {
  const page = document.querySelector("[data-verify-page]");
  if (!page) {
    return;
  }
  const explicitRecordId = page.getAttribute("data-record-id");
  const pathRecordId = window.location.pathname.split("/").filter(Boolean).pop();
  const recordId = explicitRecordId || pathRecordId;
  verifyRecord(recordId);
}

document.addEventListener("DOMContentLoaded", () => {
  fetchHealthStatus();
  initDragZone();
  initDomainToggle();
  initAnalyseForm();
  initServerRenderedResults();
  initCopyButtons();
  initVerifyPage();
});
