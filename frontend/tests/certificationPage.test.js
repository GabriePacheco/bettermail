import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const page = await readFile(
  new URL("../public/appsource-test.html", import.meta.url),
  "utf8",
);

test("certification page exposes the temporary Pro activation form", () => {
  assert.match(page, /id="certification-form"/);
  assert.match(page, /\/certification\/activate/);
  assert.match(page, /license_key/);
});

test("certification page does not expose administrative credentials", () => {
  assert.doesNotMatch(page, /ADMIN_API_SECRET/);
  assert.doesNotMatch(page, /X-Admin-Secret/i);
  assert.doesNotMatch(page, /localStorage\.setItem/);
});
