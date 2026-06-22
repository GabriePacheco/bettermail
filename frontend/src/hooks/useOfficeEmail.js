import { useCallback, useEffect, useState } from "react";

import {
  buildFinalHtmlAfterInsertBelow,
  buildFinalHtmlAfterReplace,
  extractCurrentDraftZone,
  plainTextToOutlookHtml,
} from "../utils/emailHtml";

const previewHtml = `<p>Hola Juan,</p>
<p>Necesito decir que no estoy de acuerdo con esto, pero de forma profesional.</p>`;

function ensureOffice() {
  if (!window.Office || !window.Office.context?.mailbox?.item) {
    throw new Error("Este add-in debe abrirse dentro de Outlook.");
  }
  return window.Office.context.mailbox.item;
}

function canUseOutlookItem() {
  return !!window.Office?.context?.mailbox?.item;
}

function readUserProfile() {
  const profile = window.Office?.context?.mailbox?.userProfile;

  return {
    email: profile?.emailAddress || "preview@bettermail.ai",
    display_name: profile?.displayName || "Preview User",
    account_type: "outlook",
    time_zone:
      profile?.timeZone ||
      Intl.DateTimeFormat().resolvedOptions().timeZone ||
      "",
  };
}

function readBodyHtml() {
  return new Promise((resolve, reject) => {
    try {
      const item = ensureOffice();

      item.body.getAsync(
        window.Office.CoercionType.Html,
        (result) => {
          if (result.status === window.Office.AsyncResultStatus.Succeeded) {
            resolve(result.value || "");
          } else {
            reject(new Error("No se pudo leer el cuerpo del correo."));
          }
        }
      );
    } catch (error) {
      reject(error);
    }
  });
}

function getSubjectValue(item) {
  return new Promise((resolve) => {
    try {
      if (typeof item.subject === "string") {
        resolve(item.subject);
        return;
      }

      if (item.subject?.getAsync) {
        item.subject.getAsync((result) => {
          if (result.status === window.Office.AsyncResultStatus.Succeeded) {
            resolve(result.value || "");
          } else {
            resolve("");
          }
        });
        return;
      }

      resolve("");
    } catch {
      resolve("");
    }
  });
}

function setBodyHtml(html) {
  return new Promise((resolve, reject) => {
    try {
      const item = ensureOffice();

      item.body.setAsync(
        html,
        { coercionType: window.Office.CoercionType.Html },
        (result) => {
          if (result.status === window.Office.AsyncResultStatus.Succeeded) {
            resolve(true);
          } else {
            reject(new Error("No se pudo actualizar el correo."));
          }
        }
      );
    } catch (error) {
      reject(error);
    }
  });
}

function prependBodyHtml(html) {
  return new Promise((resolve, reject) => {
    try {
      const item = ensureOffice();

      if (typeof item.body.prependAsync !== "function") {
        reject(new Error("Outlook no permite insertar la respuesta al inicio."));
        return;
      }

      item.body.prependAsync(
        html,
        { coercionType: window.Office.CoercionType.Html },
        (result) => {
          if (result.status === window.Office.AsyncResultStatus.Succeeded) {
            resolve(true);
          } else {
            reject(new Error("No se pudo insertar la respuesta al inicio."));
          }
        }
      );
    } catch (error) {
      reject(error);
    }
  });
}

async function copyToClipboard(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch {
    // Outlook WebView can block the async clipboard API. Fall back below.
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.select();

  try {
    const copied = document.execCommand("copy");
    if (!copied) {
      throw new Error("copy command failed");
    }
  } finally {
    document.body.removeChild(textarea);
  }
}

function getEmailStateFromHtml(html) {
  const parts = extractCurrentDraftZone(html);

  console.log("[BetterMail] draftText:", parts.draftText);
  console.log("[BetterMail] draftHtml length:", parts.draftHtml.length);
  console.log("[BetterMail] signatureHtml length:", parts.signatureHtml.length);
  console.log("[BetterMail] quotedHtml length:", parts.quotedHtml.length);
  console.log("[BetterMail] isReply:", parts.isReply);
  console.log("[BetterMail] isForward:", parts.isForward);

  return {
    fullHtml: html,
    ...parts,
  };
}

export function useOfficeEmail() {
  const [emailState, setEmailState] = useState(() => getEmailStateFromHtml(""));
  const [subject, setSubject] = useState("");
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState("");
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [userProfile, setUserProfile] = useState(null);

  const refreshEmail = useCallback(async () => {
    if (!canUseOutlookItem()) {
      setError("");
      setSubject("");
      setEmailState(getEmailStateFromHtml(previewHtml));
      return;
    }

    try {
      setError("");

      const item = ensureOffice();
      const [html, currentSubject] = await Promise.all([
        readBodyHtml(),
        getSubjectValue(item),
      ]);

      setEmailState(getEmailStateFromHtml(html || ""));
      setSubject(currentSubject);
    } catch (err) {
      setEmailState(getEmailStateFromHtml(""));
      setError(err.message || "No se pudo leer el correo.");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let intervalId;
    let timeoutId;

    const loadFromOffice = async ({ allowPreview = false } = {}) => {
      if (cancelled) return;

      if (!canUseOutlookItem()) {
        if (!allowPreview) return;

        setIsPreviewMode(true);
        setIsReady(true);
        setUserProfile(readUserProfile());
        setEmailState(getEmailStateFromHtml(previewHtml));
        return;
      }

      setIsPreviewMode(false);
      setIsReady(true);
      setUserProfile(readUserProfile());
      await refreshEmail();
    };

    if (!window.Office) {
      loadFromOffice({ allowPreview: true });
      return () => {
        cancelled = true;
      };
    }

    if (typeof window.Office.onReady === "function") {
      window.Office.onReady(loadFromOffice);
    } else {
      loadFromOffice();
    }

    intervalId = window.setInterval(() => {
      if (canUseOutlookItem()) {
        window.clearInterval(intervalId);
        intervalId = null;
        loadFromOffice();
      }
    }, 500);

    timeoutId = window.setTimeout(() => {
      if (!canUseOutlookItem() && !cancelled) {
        setIsPreviewMode(false);
        setIsReady(true);
        setUserProfile(readUserProfile());
        setError("Outlook no entrego el correo todavia. Cierra y vuelve a abrir BetterMail AI.");
      }

      if (intervalId) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    }, 10000);

    return () => {
      cancelled = true;
      if (intervalId) window.clearInterval(intervalId);
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [refreshEmail]);

  const commitHtml = useCallback(
    async (finalHtml) => {
      console.log("[BetterMail] finalHtml preview:", finalHtml.slice(0, 1000));

      if (!isPreviewMode) {
        await setBodyHtml(finalHtml);
      }

      setEmailState(getEmailStateFromHtml(finalHtml));
    },
    [isPreviewMode]
  );

  const replaceDraftWithText = useCallback(
    async (improvedText, mode = "rewrite_draft") => {
      if (mode === "suggest_reply" && !emailState.hasDraft && emailState.quotedHtml) {
        const replyHtml = `${plainTextToOutlookHtml(improvedText, emailState.fullHtml)}<div><br></div><div><br></div>`;

        if (!isPreviewMode) {
          await prependBodyHtml(replyHtml);
          await refreshEmail();
          return;
        }

        setEmailState(getEmailStateFromHtml(`${replyHtml}${emailState.fullHtml || ""}`));
        return;
      }

      const finalHtml = buildFinalHtmlAfterReplace({
        improvedText,
        draftHtml: emailState.draftHtml,
        signatureHtml: emailState.signatureHtml,
        quotedHtml: emailState.quotedHtml,
      });

      await commitHtml(finalHtml);
    },
    [
      commitHtml,
      emailState.draftHtml,
      emailState.fullHtml,
      emailState.hasDraft,
      emailState.quotedHtml,
      emailState.signatureHtml,
      isPreviewMode,
      refreshEmail,
    ]
  );

  const insertBelowDraftText = useCallback(
    async (improvedText, mode = "rewrite_draft") => {
      const finalHtml =
        mode === "suggest_reply"
          ? buildFinalHtmlAfterReplace({
              improvedText,
              draftHtml: emailState.draftHtml,
              signatureHtml: emailState.signatureHtml,
              quotedHtml: emailState.quotedHtml,
            })
          : buildFinalHtmlAfterInsertBelow({
              improvedText,
              draftHtml: emailState.draftHtml,
              signatureHtml: emailState.signatureHtml,
              quotedHtml: emailState.quotedHtml,
            });

      await commitHtml(finalHtml);
    },
    [commitHtml, emailState.draftHtml, emailState.quotedHtml, emailState.signatureHtml]
  );

  const applyImprovedText = useCallback(
    async (improvedText, mode = "rewrite_draft") => {
      if (mode === "suggest_reply") {
        await insertBelowDraftText(improvedText, mode);
        return;
      }

      await replaceDraftWithText(improvedText);
    },
    [insertBelowDraftText, replaceDraftWithText]
  );

  const copyText = useCallback(async (text) => {
    await copyToClipboard(text);
  }, []);

  return {
    ...emailState,
    subject,
    originalText: emailState.draftText,
    isReady,
    error,
    isPreviewMode,
    userProfile,
    refreshEmail,
    replaceDraftWithText,
    insertBelowDraftText,
    applyImprovedText,
    copyText,
  };
}
