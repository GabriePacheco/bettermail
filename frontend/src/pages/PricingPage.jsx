import { useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  CircleAlert,
  CreditCard,
  Loader2,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Star,
} from "lucide-react";

import {
  confirmPayphonePayment,
  createCheckout,
  getCheckoutDetails,
} from "../api/bettermailApi";

const BRAND_MARK = `${import.meta.env.BASE_URL}addin-icons/icon-128.png`;

const DEFAULT_PLAN = {
  id: "pro_monthly",
  name: "BetterMail Pro",
  price: 4.99,
  currency: "USD",
  monthlyLimit: 300,
};

function loadPayphoneAssets() {
  const scriptId = "payphone-box-js";
  const styleId = "payphone-box-css";

  if (!document.getElementById(styleId)) {
    const link = document.createElement("link");
    link.id = styleId;
    link.rel = "stylesheet";
    link.href = "https://cdn.payphonetodoesposible.com/box/v2.0/payphone-payment-box.css";
    document.head.appendChild(link);
  }

  if (window.PPaymentButtonBox || document.getElementById(scriptId)) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = scriptId;
    script.src = "https://cdn.payphonetodoesposible.com/box/v2.0/payphone-payment-box.js";
    script.type = "module";
    script.onload = resolve;
    script.onerror = () => reject(new Error("No se pudo cargar PayPhone."));
    document.body.appendChild(script);
  });
}

function queryUser() {
  const params = new URLSearchParams(window.location.search);

  return {
    email: params.get("email") || "",
    display_name: params.get("display_name") || "",
    account_type: params.get("account_type") || "work",
    time_zone: params.get("time_zone") || "",
  };
}

function Brand() {
  return (
    <div className="pricing-brand">
      <img className="brand-logo" src={BRAND_MARK} alt="BetterMail AI" />
      <span>BetterMail AI</span>
    </div>
  );
}

function PlanSelection({ user, onSelect, loading }) {
  return (
    <main className="pricing-shell">
      <header className="pricing-header">
        <Brand />
        <div className="pricing-secure">
          <LockKeyhole size={16} />
          Pago seguro
        </div>
      </header>

      <section className="plans-page">
        <div className="plans-heading">
          <p>Planes</p>
          <h1>Elige BetterMail Pro</h1>
        </div>

        <div className="plans-grid">
          <article className="plan-card-option">
            <h2>Trial</h2>
            <div className="plan-price">
              <strong>$0</strong>
              <span>/ 30 dias</span>
            </div>
            <p>Prueba las mejoras de IA incluidas en tu cuenta actual.</p>
            <button type="button" className="secondary-plan-button" disabled>
              Plan actual
            </button>
            <ul>
              <li>Limite gratuito inicial</li>
              <li>No requiere tarjeta</li>
              <li>Ideal para probar BetterMail</li>
            </ul>
          </article>

          <article className="plan-card-option featured">
            <div className="popular-pill">
              <Star size={14} />
              Recomendado
            </div>
            <h2>BetterMail Pro</h2>
            <div className="plan-price">
              <strong>$4.99</strong>
              <span>/ mes</span>
            </div>
            <p>Para usar BetterMail AI todos los dias desde Outlook.</p>
            <button
              type="button"
              className="primary-plan-button"
              onClick={onSelect}
              disabled={loading}
            >
              {loading ? "Preparando solicitud..." : "Continuar"}
            </button>
            <ul>
              <li>300 mejoras mensuales</li>
              <li>Tonos profesionales</li>
              <li>Reescritura y respuestas sugeridas</li>
            </ul>
          </article>
        </div>

        <div className="plans-user">
          Cuenta: <strong>{user.email || "usuario de Outlook"}</strong>
        </div>
      </section>
    </main>
  );
}

export default function PricingPage() {
  const orderId = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("order_id") || "";
  }, []);
  const payphoneReturn = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return {
      id: params.get("id") || "",
      clientTransactionId: params.get("clientTransactionId") || "",
      cardToken: params.get("ctoken") || params.get("cardToken") || "",
    };
  }, []);
  const initialCheckoutStatus = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("checkout_status") || "";
  }, []);

  const [user] = useState(queryUser);
  const [checkout, setCheckout] = useState(null);
  const [status, setStatus] = useState(
    payphoneReturn.id && payphoneReturn.clientTransactionId
      ? "confirming"
      : orderId
        ? "loading"
        : initialCheckoutStatus === "unavailable" ? "unavailable" : "plans",
  );
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const payphoneContainerRef = useRef(null);
  const renderedRef = useRef(false);
  const refreshedOrderRef = useRef(false);

  const plan = checkout?.plan || DEFAULT_PLAN;
  const price = Number(plan.price || 0);
  const monthlyLimit = Number(plan.monthlyLimit || 0);
  const contactEmail = checkout?.email || user.email;
  const isLoading = status === "loading" || status === "creating" || status === "confirming";
  const isActive = status === "active";

  const startCheckout = async () => {
    if (!user.email) {
      setStatus("unavailable");
      return;
    }

    try {
      setStatus("creating");
      setError("");
      const data = await createCheckout({
        user,
        planId: DEFAULT_PLAN.id,
        provider: "payphone_cajita",
      });

      setCheckout(data);
      setStatus("ready");
      window.history.replaceState(null, "", `?order_id=${data.orderId}`);
    } catch (err) {
      setCheckout({
        plan: DEFAULT_PLAN,
        email: user.email,
        provider: "payphone_cajita",
        paymentUnavailableReason: "payphone_checkout_unavailable",
      });
      setStatus("ready");
      setError(err.message || "");
    }
  };

  useEffect(() => {
    if (status !== "confirming") {
      return;
    }

    let cancelled = false;

    const confirmPayment = async () => {
      try {
        setError("");
        setMessage("Confirmando pago con PayPhone...");
        const result = await confirmPayphonePayment({
          id: payphoneReturn.id,
          clientTransactionId: payphoneReturn.clientTransactionId,
          cardToken: payphoneReturn.cardToken,
        });

        if (!cancelled) {
          setStatus("active");
          setCheckout({
            plan: DEFAULT_PLAN,
            provider: "payphone_cajita",
            email: user.email,
          });
          setMessage(
            result.subscriptionStatus === "active"
              ? "BetterMail Pro esta activo. Puedes volver a Outlook."
              : "Pago confirmado.",
          );
        }
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          setError(err.message || "No se pudo confirmar el pago.");
        }
      }
    };

    confirmPayment();

    return () => {
      cancelled = true;
    };
  }, [payphoneReturn, status, user.email]);

  useEffect(() => {
    if (!orderId) {
      return;
    }

    let cancelled = false;

    const loadCheckout = async () => {
      try {
        const data = await getCheckoutDetails({ orderId });

        if (!cancelled) {
          if (!data.payphone && data.email && !refreshedOrderRef.current) {
            refreshedOrderRef.current = true;
            const refreshed = await createCheckout({
              user: {
                email: data.email,
                display_name: user.display_name,
                account_type: user.account_type,
                time_zone: user.time_zone,
              },
              planId: DEFAULT_PLAN.id,
              provider: "payphone_cajita",
            });

            if (!cancelled) {
              renderedRef.current = false;
              setCheckout(refreshed);
              setStatus("ready");
              window.history.replaceState(null, "", `?order_id=${refreshed.orderId}`);
            }
            return;
          }

          renderedRef.current = false;
          setCheckout(data);
          setStatus("ready");
        }
      } catch (err) {
        if (!cancelled) {
          setStatus("error");
          setError(err.message || "No se pudo cargar la solicitud.");
        }
      }
    };

    loadCheckout();

    return () => {
      cancelled = true;
    };
  }, [orderId, user.account_type, user.display_name, user.time_zone]);

  useEffect(() => {
    if (
      status !== "ready" ||
      !checkout?.payphone ||
      !payphoneContainerRef.current ||
      renderedRef.current
    ) {
      return;
    }

    renderedRef.current = true;

    const renderPayphone = async () => {
      try {
        await loadPayphoneAssets();

        const PayphoneBox = window.PPaymentButtonBox;

        if (!PayphoneBox) {
          throw new Error("PayPhone no esta disponible.");
        }

        payphoneContainerRef.current.innerHTML = "";

        const payphoneOptions = {
          token: checkout.payphone.token,
          clientTransactionId: checkout.payphone.clientTransactionId,
          amount: checkout.payphone.amount,
          amountWithoutTax: checkout.payphone.amountWithoutTax,
          amountWithTax: 0,
          tax: 0,
          service: 0,
          tip: 0,
          currency: checkout.payphone.currency,
          reference: checkout.payphone.reference,
          email: contactEmail || undefined,
          defaultMethod: checkout.payphone.defaultMethod || "card",
          lang: "es",
          timeZone: -5,
          backgroundColor: "#1d4ed8",
        };

        if (checkout.payphone.storeId) {
          payphoneOptions.storeId = checkout.payphone.storeId;
        }

        new PayphoneBox(payphoneOptions).render("payphone-box");
      } catch (err) {
        setError(err.message || "No se pudo cargar PayPhone.");
      }
    };

    renderPayphone();
  }, [checkout, contactEmail, status]);

  if (status === "plans") {
    return <PlanSelection user={user} onSelect={startCheckout} loading={isLoading} />;
  }

  return (
    <main className="pricing-shell">
      <header className="pricing-header">
        <Brand />
        <div className="pricing-secure">
          <LockKeyhole size={16} />
          Pago seguro
        </div>
      </header>

      <section className="pricing-layout">
        <div className="pricing-main">
          <div className="contact-block">
            <div className="pricing-section-title">
              <span>Contacto</span>
            </div>
            <div className="contact-input">
              <Mail size={18} />
              {contactEmail || "Email"}
            </div>
          </div>

          <div className="payment-block">
            <div className="pricing-section-title compact">
              <span>{isActive ? "Compra realizada" : "Pago"}</span>
              <small>
                {isActive
                  ? "BetterMail Pro ya esta activo para esta cuenta."
                  : "Ingresa tu tarjeta en la cajita segura de PayPhone."}
              </small>
            </div>

            {isLoading && (
              <div className="pricing-state">
                <Loader2 className="spin-icon" size={18} />
                {status === "confirming" ? "Confirmando pago..." : "Cargando checkout..."}
              </div>
            )}

            {isActive && (
              <div className="payment-success-panel">
                <div className="payment-success-icon">
                  <Check size={24} />
                </div>
                <div>
                  <strong>BetterMail Pro esta activo</strong>
                  <p>La compra se confirmo correctamente. Puedes cerrar esta ventana y volver a Outlook.</p>
                </div>
              </div>
            )}

            {!isLoading && !isActive && status !== "error" && (
              <>
                {checkout?.payphone ? (
                  <div className="payphone-payment-box">
                    <div className="payphone-card-head">
                      <div className="payment-pending-icon">
                        <CreditCard size={22} />
                      </div>
                      <div>
                        <strong>Tarjeta de credito o debito</strong>
                        <p>PayPhone procesa los datos de tarjeta. BetterMail solo recibe la confirmacion.</p>
                      </div>
                    </div>
                    <div id="payphone-box" ref={payphoneContainerRef} />
                  </div>
                ) : (
                  <div className="payment-pending-panel">
                    <div className="payment-pending-icon">
                      <CreditCard size={22} />
                    </div>
                    <div>
                      <strong>No se pudo activar la cajita</strong>
                      <p>
                        Esta orden no trae los datos de pago necesarios. Cierra esta ventana y vuelve a
                        abrir Hazte Pro para crear una solicitud nueva.
                      </p>
                    </div>
                  </div>
                )}

                <div className="pricing-message">
                  Para tokenizar la tarjeta, PayPhone debe tener habilitada la funcionalidad en tu comercio.
                </div>
              </>
            )}

            {message && <div className="pricing-message">{message}</div>}

            {error && (
              <div className="pricing-error">
                <CircleAlert size={17} />
                {error}
              </div>
            )}
          </div>
        </div>

        <aside className="pricing-summary">
          <div className="summary-product">
            <img className="summary-product-logo" src={BRAND_MARK} alt="" />
            <div>
              <p className="summary-product-name">BetterMail Pro</p>
              <p className="summary-product-meta">Suscripcion mensual</p>
            </div>
            <strong>${price.toFixed(2)}</strong>
          </div>

          <div className="summary-lines">
            <div className="summary-line">
              <span>Subtotal recurrente</span>
              <strong>${price.toFixed(2)}</strong>
            </div>
            <div className="summary-line muted">
              <span>Impuestos</span>
              <span>Por definir con el proveedor</span>
            </div>
          </div>

          <div className="summary-total">
            <span>Total</span>
            <strong>USD ${price.toFixed(2)}</strong>
          </div>

          <div className="summary-renewal">
            ${price.toFixed(2)} cada mes hasta cancelar.
          </div>

          <div className="summary-security">
            <ShieldCheck size={17} />
            BetterMail no almacena datos de tarjeta. PayPhone puede devolver un token para cobros futuros.
          </div>

          <div className="summary-features">
            <div>
              <Check size={15} />
              {monthlyLimit} mejoras mensuales
            </div>
            <div>
              <Check size={15} />
              Tonos profesionales
            </div>
            <div>
              <Check size={15} />
              Respuestas sugeridas
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
