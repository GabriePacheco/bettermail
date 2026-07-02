import assert from "node:assert/strict";
import test from "node:test";

import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.DOMParser = dom.window.DOMParser;
globalThis.Node = dom.window.Node;
globalThis.NodeFilter = dom.window.NodeFilter;

const {
  buildFinalHtmlAfterReplace,
  extractCurrentDraftZone,
} = await import("../src/utils/emailHtml.js");

test("replace preserves an Outlook signature and quoted history", () => {
  const source = [
    "<div>borador original</div>",
    '<div id="Signature"><strong>Gabriel</strong><br>BetterMail</div>',
    '<div class="OutlookMessageHeader">From: client@example.com<br>Subject: Informe</div>',
  ].join("");
  const parts = extractCurrentDraftZone(source);

  assert.match(parts.signatureHtml, /id="Signature"/);
  assert.match(parts.quotedHtml, /OutlookMessageHeader/);

  const result = buildFinalHtmlAfterReplace({
    improvedText: "Borrador mejorado",
    ...parts,
  });

  assert.match(result, /Borrador mejorado/);
  assert.match(result, /<strong>Gabriel<\/strong>/);
  assert.match(result, /client@example\.com/);
});

test("detects and preserves a nested Outlook signature", () => {
  const source = [
    "<div>",
    "<div>Necesito confirmar la reunion.</div>",
    '<div data-outlook-signature="true"><span>Ana Perez</span><br><span>Ventas</span></div>',
    "</div>",
  ].join("");
  const parts = extractCurrentDraftZone(source);

  assert.equal(parts.draftText, "Necesito confirmar la reunion.");
  assert.match(parts.signatureHtml, /data-outlook-signature="true"/);

  const result = buildFinalHtmlAfterReplace({
    improvedText: "Confirmo la reunion.",
    ...parts,
  });

  assert.match(result, /Ana Perez/);
  assert.match(result, /Ventas/);
});
