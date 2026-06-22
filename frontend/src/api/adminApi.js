const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

function requireApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error("El API administrativo no esta configurado.");
  }
  return API_BASE_URL;
}

async function adminRequest(path, { secret, email, reason, planId }) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Secret": secret,
    },
    body: JSON.stringify({
      email,
      ...(reason ? { reason } : {}),
      ...(planId ? { plan_id: planId } : {}),
    }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Clave administrativa incorrecta.");
    }
    if (response.status === 404) {
      throw new Error("Usuario no encontrado.");
    }
    if (response.status === 503) {
      throw new Error("El acceso administrativo no esta configurado.");
    }

    let message = "No se pudo completar la accion administrativa.";
    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep the safe default message.
    }
    throw new Error(message);
  }

  return response.json();
}

export function findAdminUser({ secret, email }) {
  return adminRequest("/billing/admin/user", { secret, email });
}

export function activateAdminUser({ secret, email, reason }) {
  return adminRequest("/billing/admin/manual-activate", {
    secret,
    email,
    reason,
    planId: "pro_monthly",
  });
}

export function blockAdminUser({ secret, email, reason }) {
  return adminRequest("/billing/admin/block", { secret, email, reason });
}

export function unblockAdminUser({ secret, email, reason }) {
  return adminRequest("/billing/admin/unblock", { secret, email, reason });
}

export function cancelAdminUser({ secret, email, reason }) {
  return adminRequest("/billing/admin/cancel", { secret, email, reason });
}

export function expireAdminUser({ secret, email, reason }) {
  return adminRequest("/billing/admin/expire", { secret, email, reason });
}

export async function getOpenAICosts({ secret, days = 30 }) {
  const response = await fetch(
    `${requireApiBaseUrl()}/billing/admin/openai-costs?days=${days}`,
    {
      headers: { "X-Admin-Secret": secret },
    },
  );

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Clave administrativa incorrecta.");
    }
    throw new Error("No se pudo consultar el costo de OpenAI.");
  }

  return response.json();
}
