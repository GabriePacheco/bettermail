const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const APP_SECRET =
  import.meta.env.VITE_APP_SHARED_SECRET || import.meta.env.VITE_API_KEY || "";

function getHeaders() {
  return {
    "Content-Type": "application/json",
    "x-app-secret": APP_SECRET,
  };
}

function normalizeUsage(data) {
  const limit = Number(data.trial_limit ?? data.trialLimit ?? 0);
  const used = Number(data.trial_used ?? data.trialUsed ?? 0);

  return {
    status: data.status || "trial",
    remaining: Number(data.remaining ?? Math.max(limit - used, 0)),
    limit,
    used,
  };
}

export async function getUsageStatus({ user }) {
  const response = await fetch(`${API_BASE_URL}/usage/status`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(user),
  });

  if (!response.ok) {
    throw new Error("No se pudo obtener el uso del plan.");
  }

  return normalizeUsage(await response.json());
}

export async function rewriteEmail({
  text,
  tone,
  user,
  source = "outlook_addin",
  mode = "rewrite_draft",
  context,
}) {
  const response = await fetch(`${API_BASE_URL}/rewrite`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      user,
      text: text || "",
      tone,
      source,
      mode,
      context,
    }),
  });

  if (!response.ok) {
    let message = "No se pudo reescribir el correo.";

    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  const data = await response.json();

  if (data.allowed === false) {
    throw new Error(data.message || "No tienes creditos disponibles.");
  }

  return {
    usage: normalizeUsage(data),
    improvedText:
      data.improved_text ||
      data.rewritten_text ||
      data.result ||
      "",
  };
}
