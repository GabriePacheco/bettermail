const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
const PUBLIC_BASE_URL =
  (import.meta.env.VITE_PUBLIC_BASE_URL || "https://bettermailai.web.app").replace(/\/+$/, "");
const APP_SECRET =
  import.meta.env.VITE_APP_SHARED_SECRET || import.meta.env.VITE_API_KEY || "";

function requireApiBaseUrl() {
  if (!API_BASE_URL) {
    throw new Error("No pudimos conectar con BetterMail AI en este momento.");
  }

  return API_BASE_URL;
}

function getHeaders() {
  return {
    "Content-Type": "application/json",
    "x-app-secret": APP_SECRET,
  };
}

function normalizeUsage(data) {
  const plan = data.plan || "trial";
  const fallbackLimit =
    plan === "pro"
      ? data.monthlyLimit ?? data.monthly_limit
      : data.trial_limit ?? data.trialLimit;
  const fallbackUsed =
    plan === "pro"
      ? data.monthlyUsed ?? data.monthly_used
      : data.trial_used ?? data.trialUsed;
  const limit = Number(data.limit ?? fallbackLimit ?? 0);
  const used = Number(data.used ?? fallbackUsed ?? 0);

  return {
    allowed: data.allowed ?? ["active", "trial"].includes(data.status),
    plan,
    status: data.status || "trial",
    remaining: Number(data.remaining ?? Math.max(limit - used, 0)),
    limit,
    used,
    trialLimit: Number(data.trial_limit ?? data.trialLimit ?? 0),
    trialUsed: Number(data.trial_used ?? data.trialUsed ?? 0),
    monthlyLimit: Number(data.monthlyLimit ?? data.monthly_limit ?? 0),
    monthlyUsed: Number(data.monthlyUsed ?? data.monthly_used ?? 0),
    upgradeRequired: Boolean(data.upgradeRequired ?? data.upgrade_required ?? false),
  };
}

function buildCheckoutUrl(checkoutUrl) {
  if (!checkoutUrl) return "";

  if (/^https?:\/\//i.test(checkoutUrl)) {
    return checkoutUrl;
  }

  return `${requireApiBaseUrl()}${checkoutUrl}`;
}

export function getPricingUrl(params = {}) {
  const url = new URL("/pricing", PUBLIC_BASE_URL);

  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      url.searchParams.set(key, value);
    }
  });

  return url.toString();
}

export async function getUsageStatus({ user }) {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/usage/status`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(user),
  });

  if (!response.ok) {
    throw new Error("No se pudo obtener el uso del plan.");
  }

  return normalizeUsage(await response.json());
}

export async function getPlans() {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/plans`, {
    method: "GET",
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error("No se pudieron cargar los planes.");
  }

  return response.json();
}

export async function createCheckout({
  user,
  planId = "pro_monthly",
  provider = "payphone_cajita",
  source = "outlook_addin",
}) {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/billing/checkout`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      user,
      plan_id: planId,
      provider,
      source,
    }),
  });

  if (!response.ok) {
    let message = "No se pudo iniciar el checkout.";

    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  const data = await response.json();

  return {
    checkoutUrl: buildCheckoutUrl(data.checkout_url),
    orderId: data.order_id,
    status: data.status,
    provider: data.provider,
    paymentUnavailableReason: data.payment_unavailable_reason,
    plan: data.plan,
    payphone: normalizePayphone(data),
  };
}

export async function getCheckoutDetails({ orderId }) {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/billing/checkout/${orderId}`, {
    method: "GET",
    headers: getHeaders(),
  });

  if (!response.ok) {
    let message = "No se pudo cargar la orden de pago.";

    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  const data = await response.json();

  return {
    checkoutUrl: buildCheckoutUrl(data.checkout_url),
    orderId: data.order_id,
    status: data.status,
    provider: data.provider,
    paymentUnavailableReason: data.payment_unavailable_reason,
    plan: data.plan,
    email: data.email,
    source: data.source,
    payphone: normalizePayphone(data),
  };
}

function normalizePayphone(data) {
  if (!data.payphone_token) {
    return null;
  }

  return {
    token: data.payphone_token,
    storeId: data.payphone_store_id,
    clientTransactionId: data.payphone_client_transaction_id,
    amount: Number(data.payphone_amount || 0),
    amountWithoutTax: Number(data.payphone_amount_without_tax || data.payphone_amount || 0),
    currency: data.payphone_currency || "USD",
    reference: data.payphone_reference || "BetterMail Pro mensual",
    defaultMethod: data.payphone_default_method || "card",
  };
}

export async function confirmPayphonePayment({ id, clientTransactionId, cardToken }) {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/billing/payphone/confirm`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      id: Number(id),
      client_transaction_id: clientTransactionId,
      card_token: cardToken || null,
    }),
  });

  if (!response.ok) {
    let message = "No se pudo confirmar el pago.";

    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  return response.json();
}

export async function getBillingStatus({ user }) {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/billing/status`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ user }),
  });

  if (!response.ok) {
    throw new Error("No se pudo obtener el estado de billing.");
  }

  return normalizeBillingStatus(await response.json());
}

function normalizeBillingStatus(data) {
  return {
    plan: data.plan || "trial",
    status: data.status || "trial",
    subscriptionStatus: data.subscriptionStatus || data.subscription_status || null,
    monthlyLimit: Number(data.monthlyLimit ?? data.monthly_limit ?? 0),
    monthlyUsed: Number(data.monthlyUsed ?? data.monthly_used ?? 0),
    currentPeriodEnd: data.currentPeriodEnd || data.current_period_end || null,
    gracePeriodEnd: data.gracePeriodEnd || data.grace_period_end || null,
    nextRenewalAttemptAt:
      data.nextRenewalAttemptAt || data.next_renewal_attempt_at || null,
    cancelAtPeriodEnd: Boolean(
      data.cancelAtPeriodEnd ?? data.cancel_at_period_end ?? false,
    ),
    autoRenew: Boolean(data.autoRenew ?? data.auto_renew ?? false),
    paymentActionRequired: Boolean(
      data.paymentActionRequired ?? data.payment_action_required ?? false,
    ),
    renewalFailureCount: Number(
      data.renewalFailureCount ?? data.renewal_failure_count ?? 0,
    ),
  };
}

async function updateSubscription(path, { user, reason }) {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ user, reason: reason || null }),
  });

  if (!response.ok) {
    let message = "No se pudo actualizar la suscripcion.";
    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      // Keep default message.
    }
    throw new Error(message);
  }

  return normalizeBillingStatus(await response.json());
}

export function cancelSubscription({ user, reason }) {
  return updateSubscription("/billing/cancel", { user, reason });
}

export function reactivateSubscription({ user }) {
  return updateSubscription("/billing/reactivate", { user });
}

export async function rewriteEmail({
  text,
  tone,
  user,
  source = "outlook_addin",
  mode = "rewrite_draft",
  context,
}) {
  const apiBaseUrl = requireApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/rewrite`, {
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
    const error = new Error(data.message || "No tienes creditos disponibles.");
    error.usage = normalizeUsage(data);
    throw error;
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
