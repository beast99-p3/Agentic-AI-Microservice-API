const responseBox = document.getElementById("responseBox");
const streamBox = document.getElementById("streamBox");
const previewBox = document.getElementById("previewBox");
const healthBadge = document.getElementById("healthBadge");
const finalAnswerBox = document.getElementById("finalAnswerBox");
const terminationBadge = document.getElementById("terminationBadge");
const usageBadge = document.getElementById("usageBadge");
const opsBox = document.getElementById("opsBox");

const runForm = document.getElementById("runForm");
const healthBtn = document.getElementById("healthBtn");
const streamBtn = document.getElementById("streamBtn");
const previewBtn = document.getElementById("previewBtn");
const toolsBtn = document.getElementById("toolsBtn");

function parseTools(text) {
  return text
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function payloadFromForm() {
  return {
    task: document.getElementById("task").value,
    max_steps: Number(document.getElementById("maxSteps").value),
    max_tool_calls: Number(document.getElementById("maxToolCalls").value),
    max_runtime_seconds: Number(document.getElementById("maxRuntime").value),
    temperature: Number(document.getElementById("temperature").value),
    allowed_tools: parseTools(document.getElementById("allowedTools").value),
  };
}

function pretty(data) {
  return JSON.stringify(data, null, 2);
}

function titleCase(value) {
  if (!value) return "Unknown";
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function renderAgentResponse(body) {
  const finalAnswer = body.final_answer || "No final answer returned.";
  const reason = titleCase(body.termination_reason);
  const steps = body?.budget_usage?.steps_used ?? 0;
  const limit = body?.budget_usage?.steps_limit ?? "-";
  const toolsUsed = body?.budget_usage?.tool_calls_used ?? 0;

  finalAnswerBox.textContent = finalAnswer;
  terminationBadge.textContent = `Termination: ${reason}`;
  usageBadge.textContent = `Steps ${steps}/${limit} • Tool Calls ${toolsUsed}`;

  const warnings = body.warnings || [];
  const toolCalls = body.tool_calls || [];
  const summary = {
    warnings,
    tool_calls: toolCalls,
  };
  opsBox.textContent = pretty(summary);

  responseBox.textContent = pretty(body);
}

async function checkHealth() {
  healthBadge.textContent = "Checking...";
  try {
    const res = await fetch("/health");
    const body = await res.json();
    if (!res.ok) {
      throw new Error(pretty(body));
    }
    healthBadge.textContent = `Healthy • ${body.version}`;
  } catch (error) {
    healthBadge.textContent = "Unhealthy";
    responseBox.textContent = String(error);
  }
}

async function runAgent() {
  finalAnswerBox.textContent = "Running...";
  terminationBadge.textContent = "Termination: Pending";
  usageBadge.textContent = "Running...";
  responseBox.textContent = "Running...";
  opsBox.textContent = "Running...";
  try {
    const res = await fetch("/agent/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payloadFromForm()),
    });
    const body = await res.json();
    renderAgentResponse(body);
  } catch (error) {
    const text = String(error);
    finalAnswerBox.textContent = text;
    responseBox.textContent = text;
    opsBox.textContent = text;
    terminationBadge.textContent = "Termination: Error";
    usageBadge.textContent = "-";
  }
}

async function previewPrompt() {
  previewBox.textContent = "Building prompt preview...";
  const runPayload = payloadFromForm();
  const payload = {
    task: runPayload.task,
    max_steps: runPayload.max_steps,
    max_tool_calls: runPayload.max_tool_calls,
    max_runtime_seconds: runPayload.max_runtime_seconds,
    allowed_tools: runPayload.allowed_tools,
  };

  try {
    const res = await fetch("/prompt/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json();
    previewBox.textContent = pretty(body);
  } catch (error) {
    previewBox.textContent = String(error);
  }
}

async function listTools() {
  finalAnswerBox.textContent = "Loaded tools list.";
  terminationBadge.textContent = "Termination: N/A";
  usageBadge.textContent = "-";
  responseBox.textContent = "Loading tools...";
  opsBox.textContent = "Tool listing...";
  try {
    const res = await fetch("/tools");
    const body = await res.json();
    responseBox.textContent = pretty(body);
    opsBox.textContent = pretty({ tool_count: body.tools?.length ?? 0, tool_names: (body.tools || []).map((t) => t.name) });
  } catch (error) {
    const text = String(error);
    responseBox.textContent = text;
    opsBox.textContent = text;
  }
}

async function streamAgent() {
  streamBox.textContent = "Streaming...\n";

  const res = await fetch("/agent/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payloadFromForm()),
  });

  if (!res.body) {
    streamBox.textContent += "No response stream available.";
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n").filter((line) => line.startsWith("data: "));
    for (const line of lines) {
      const text = line.slice(6);
      try {
        const parsed = JSON.parse(text);
        streamBox.textContent += `${pretty(parsed)}\n\n`;
      } catch {
        streamBox.textContent += `${text}\n`;
      }
    }
    streamBox.scrollTop = streamBox.scrollHeight;
  }
}

runForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runAgent();
});

healthBtn.addEventListener("click", checkHealth);
streamBtn.addEventListener("click", streamAgent);
previewBtn.addEventListener("click", previewPrompt);
toolsBtn.addEventListener("click", listTools);

checkHealth();
