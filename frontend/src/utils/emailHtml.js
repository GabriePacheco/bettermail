const REPLY_MARKERS = [
  "-----original message-----",
  "original message",
  "mensaje original",
  "forwarded message",
  "mensaje reenviado",
  "reenviado",
  "begin forwarded message",
  "de:",
  "enviado:",
  "para:",
  "asunto:",
  "from:",
  "sent:",
  "to:",
  "subject:",
  "________________________________",
];

const HEADER_MARKERS = [
  "de:",
  "enviado:",
  "para:",
  "asunto:",
  "from:",
  "sent:",
  "to:",
  "subject:",
];

const SIGNATURE_MARKERS = [
  "--",
  "saludos,",
  "saludos cordiales,",
  "atentamente,",
  "cordialmente,",
];

const SIGNATURE_SELECTOR = [
  "#Signature",
  "._MailAutoSig",
  ".ms-outlook-signature",
  "[data-outlook-signature]",
  "[data-signature]",
  "[id*='signature' i]",
  "[class*='signature' i]",
  "[id*='autosig' i]",
  "[class*='autosig' i]",
].join(",");

const QUOTE_SELECTOR = [
  "blockquote",
  ".gmail_quote",
  ".yahoo_quoted",
  ".appendonsend",
  ".WordSection1",
  ".OutlookMessageHeader",
  "[class*='gmail_quote']",
  "[class*='yahoo_quoted']",
  "[class*='appendonsend']",
  "[class*='WordSection']",
  "[class*='OutlookMessageHeader']",
  "[class*='ms-outlook']",
  "[class*='quote']",
  "[class*='quoted']",
  "[class*='reply']",
  "[id*='quote']",
  "[id*='quoted']",
  "[id*='reply']",
].join(",");

const DEFAULT_OUTLOOK_STYLE =
  "font-family: Aptos, Calibri, Arial, sans-serif; font-size: 12pt; color: inherit;";

function createDocument(html) {
  return new DOMParser().parseFromString(html || "", "text/html");
}

function serializeNodes(nodes) {
  const container = document.createElement("div");
  nodes.forEach((node) => container.appendChild(node.cloneNode(true)));
  return container.innerHTML;
}

function serializeFragment(fragment) {
  const container = document.createElement("div");
  container.appendChild(fragment.cloneNode(true));
  return container.innerHTML;
}

export function htmlToPlainText(html) {
  if (!html) return "";

  const doc = createDocument(html);
  doc.querySelectorAll("script, style, meta, title").forEach((node) => node.remove());
  doc.querySelectorAll("br").forEach((node) => node.replaceWith("\n"));
  doc.querySelectorAll("p, div, li, tr, table, blockquote").forEach((node) => {
    node.appendChild(doc.createTextNode("\n"));
  });

  return (doc.body.textContent || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\s+\n/g, "\n")
    .replace(/\n\s+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function isMeaningfulText(text) {
  return !!text?.replace(/[\s\u00a0\u200b-\u200d\ufeff]/g, "").trim();
}

export function limitText(text, maxChars = 2500) {
  const cleaned = text || "";
  if (cleaned.length <= maxChars) return cleaned;
  return cleaned.slice(0, maxChars).trimEnd();
}

function escapeHtml(text) {
  return (text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getNodeText(node) {
  const wrapper = document.createElement("div");
  wrapper.appendChild(node.cloneNode(true));
  return htmlToPlainText(wrapper.innerHTML).toLowerCase();
}

function countHeaderMarkers(lines) {
  return lines.reduce((count, line) => {
    const normalized = line.trim().toLowerCase();
    return HEADER_MARKERS.some((marker) => normalized.startsWith(marker))
      ? count + 1
      : count;
  }, 0);
}

function isMarkerText(text) {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;

  return (
    REPLY_MARKERS.some((marker) => normalized.startsWith(marker)) ||
    /^on\s.+wrote:$/i.test(text.trim()) ||
    /^el\s.+escribi[oó]:$/i.test(text.trim()) ||
    /^le\s.+escribi[oó]:$/i.test(text.trim())
  );
}

function isForwardMarkerText(text) {
  const normalized = (text || "").trim().toLowerCase();
  return [
    "forwarded message",
    "mensaje reenviado",
    "reenviado",
    "begin forwarded message",
  ].some((marker) => normalized.includes(marker));
}

function nodeLooksLikeQuoteStart(node) {
  if (node.nodeType !== Node.ELEMENT_NODE) return false;

  if (node.matches?.(QUOTE_SELECTOR) || node.querySelector?.(QUOTE_SELECTOR)) {
    return true;
  }

  const text = getNodeText(node);
  if (isMarkerText(text)) return true;

  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 8);

  return lines.some(isMarkerText) || countHeaderMarkers(lines) >= 2;
}

function findQuoteStartIndex(nodes) {
  return nodes.findIndex((node) => nodeLooksLikeQuoteStart(node));
}

function isQuoteStartElement(element) {
  if (element.nodeType !== Node.ELEMENT_NODE) return false;
  return nodeLooksLikeQuoteStart(element);
}

function findNestedQuoteStart(body) {
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_ELEMENT);
  let node = walker.nextNode();

  while (node) {
    if (isQuoteStartElement(node)) {
      return node;
    }

    node = walker.nextNode();
  }

  return null;
}

function splitByNestedQuoteStart(doc, quoteStartNode) {
  const draftRange = doc.createRange();
  draftRange.setStart(doc.body, 0);
  draftRange.setEndBefore(quoteStartNode);

  const quotedRange = doc.createRange();
  quotedRange.setStartBefore(quoteStartNode);
  quotedRange.setEnd(doc.body, doc.body.childNodes.length);

  return {
    draftHtml: serializeFragment(draftRange.cloneContents()),
    quotedHtml: serializeFragment(quotedRange.cloneContents()),
  };
}

function findSignatureStartIndex(nodes) {
  if (nodes.length < 2) return -1;

  for (let index = nodes.length - 1; index >= 1; index -= 1) {
    const text = htmlToPlainText(serializeNodes(nodes.slice(index))).toLowerCase();
    const lines = text
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    if (!lines.length || lines.length > 5) continue;

    const hasMarker = SIGNATURE_MARKERS.some((marker) =>
      lines[0].startsWith(marker)
    );
    const trailingLinesAreShort = lines.slice(1).every((line) => line.length <= 80);

    if (hasMarker && trailingLinesAreShort) {
      return index;
    }
  }

  return -1;
}

function splitSignatureHtml(draftHtml) {
  const doc = createDocument(draftHtml);
  const nodes = Array.from(doc.body.childNodes);
  const signatureElement = doc.body.querySelector(SIGNATURE_SELECTOR);

  if (signatureElement) {
    const draftRange = doc.createRange();
    draftRange.setStart(doc.body, 0);
    draftRange.setEndBefore(signatureElement);

    const signatureRange = doc.createRange();
    signatureRange.setStartBefore(signatureElement);
    signatureRange.setEnd(doc.body, doc.body.childNodes.length);

    return {
      draftHtml: serializeFragment(draftRange.cloneContents()),
      signatureHtml: serializeFragment(signatureRange.cloneContents()),
    };
  }

  const signatureStartIndex = findSignatureStartIndex(nodes);

  if (signatureStartIndex < 0) {
    return {
      draftHtml,
      signatureHtml: "",
    };
  }

  return {
    draftHtml: serializeNodes(nodes.slice(0, signatureStartIndex)),
    signatureHtml: serializeNodes(nodes.slice(signatureStartIndex)),
  };
}

export function extractOutlookBaseStyle(baseHtml) {
  if (!baseHtml) return DEFAULT_OUTLOOK_STYLE;

  const doc = createDocument(baseHtml);
  const styled = Array.from(doc.body.querySelectorAll("div, p, span, font")).find(
    (node) => isMeaningfulText(node.textContent || "") && node.getAttribute("style")
  );
  const style = styled?.getAttribute("style")?.trim();

  if (!style) return DEFAULT_OUTLOOK_STYLE;

  const usefulStyles = style
    .split(";")
    .map((part) => part.trim())
    .filter((part) =>
      /^(font-family|font-size|color|line-height)\s*:/i.test(part)
    );

  return usefulStyles.length ? `${usefulStyles.join("; ")};` : DEFAULT_OUTLOOK_STYLE;
}

function getBaseStyleAttribute(baseHtml) {
  return ` style="${escapeHtml(extractOutlookBaseStyle(baseHtml))}"`;
}

export function plainTextToOutlookHtml(text, baseHtml = "") {
  if (!isMeaningfulText(text)) return "";

  const style = getBaseStyleAttribute(baseHtml);
  const lines = (text || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");

  return lines
    .map((line) =>
      line.trim()
        ? `<div${style}>${escapeHtml(line)}</div>`
        : `<div${style}><br></div>`
    )
    .join("");
}

export function plainTextToHtml(text, baseHtml = "") {
  return plainTextToOutlookHtml(text, baseHtml);
}

function getSafeQuotedFragment(quotedHtml) {
  return (quotedHtml || "").replace(/\s+/g, " ").trim().slice(0, 160);
}

function assertQuotedHtmlPreserved(finalHtml, quotedHtml) {
  if (!quotedHtml) return;

  const fragment = getSafeQuotedFragment(quotedHtml);
  if (fragment && !finalHtml.replace(/\s+/g, " ").includes(fragment)) {
    throw new Error("Riesgo de borrar historial. Reemplazo cancelado.");
  }
}

function assertSignatureHtmlPreserved(finalHtml, signatureHtml) {
  if (!signatureHtml) return;

  const fragment = getSafeQuotedFragment(signatureHtml);
  if (fragment && !finalHtml.replace(/\s+/g, " ").includes(fragment)) {
    throw new Error("Riesgo de borrar la firma. Reemplazo cancelado.");
  }
}

function buildQuoteSeparator(baseHtml = "") {
  const style = getBaseStyleAttribute(baseHtml);
  return `<div${style}><br></div><div${style}><br></div>`;
}

function appendQuotedWithSeparator(contentHtml, quotedHtml, baseHtml = "") {
  if (!quotedHtml) return contentHtml || "";
  return `${contentHtml || ""}${buildQuoteSeparator(baseHtml)}${quotedHtml}`;
}

export function mergeImprovedWithQuoted(improvedHtml, quotedHtml) {
  return appendQuotedWithSeparator(improvedHtml, quotedHtml, improvedHtml);
}

export function insertImprovedBelowDraft(draftHtml, improvedHtml, quotedHtml) {
  return appendQuotedWithSeparator(`${draftHtml || ""}${improvedHtml || ""}`, quotedHtml, draftHtml);
}

export function buildFinalHtmlAfterReplace({
  improvedText,
  draftHtml,
  signatureHtml,
  quotedHtml,
}) {
  const improvedDraftHtml = plainTextToOutlookHtml(improvedText, draftHtml);
  const finalHtml = appendQuotedWithSeparator(
    `${improvedDraftHtml || ""}${signatureHtml || ""}`,
    quotedHtml,
    draftHtml
  );

  assertQuotedHtmlPreserved(finalHtml, quotedHtml);
  assertSignatureHtmlPreserved(finalHtml, signatureHtml);
  return finalHtml;
}

export function buildFinalHtmlAfterInsertBelow({
  improvedText,
  draftHtml,
  signatureHtml,
  quotedHtml,
}) {
  const improvedHtml = plainTextToOutlookHtml(improvedText, draftHtml);
  const finalHtml = appendQuotedWithSeparator(
    `${draftHtml || ""}${improvedHtml || ""}${signatureHtml || ""}`,
    quotedHtml,
    draftHtml
  );

  assertQuotedHtmlPreserved(finalHtml, quotedHtml);
  assertSignatureHtmlPreserved(finalHtml, signatureHtml);
  return finalHtml;
}

export function extractCurrentDraftZone(html) {
  const doc = createDocument(html);
  const nodes = Array.from(doc.body.childNodes);

  if (!nodes.length) {
    return {
      draftHtml: "",
      draftText: "",
      signatureHtml: "",
      quotedHtml: "",
      quotedText: "",
      isReply: false,
      isForward: false,
      hasDraft: false,
    };
  }

  const quoteStartIndex = findQuoteStartIndex(nodes);
  let isReply = quoteStartIndex >= 0;
  let draftHtml;
  let quotedHtml;

  if (isReply) {
    draftHtml = serializeNodes(nodes.slice(0, quoteStartIndex));
    quotedHtml = serializeNodes(nodes.slice(quoteStartIndex));
  } else {
    const nestedQuoteStart = findNestedQuoteStart(doc.body);
    isReply = !!nestedQuoteStart;

    if (nestedQuoteStart) {
      const split = splitByNestedQuoteStart(doc, nestedQuoteStart);
      draftHtml = split.draftHtml;
      quotedHtml = split.quotedHtml;
    } else {
      draftHtml = serializeNodes(nodes);
      quotedHtml = "";
    }
  }

  const signatureSplit = splitSignatureHtml(draftHtml);
  draftHtml = signatureSplit.draftHtml;

  const draftText = htmlToPlainText(draftHtml);
  const quotedText = htmlToPlainText(quotedHtml);
  const isForward = isForwardMarkerText(quotedHtml) || isForwardMarkerText(quotedText);

  return {
    draftHtml,
    draftText,
    signatureHtml: signatureSplit.signatureHtml,
    quotedHtml,
    quotedText,
    isReply,
    isForward,
    hasDraft: isMeaningfulText(draftText),
  };
}

export function splitReplyHtml(html) {
  return extractCurrentDraftZone(html);
}
