import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");
const projectRoot = path.resolve(frontendDir, "..");
const sourceManifest = path.join(projectRoot, "manifest.xml");
const publicManifest = path.join(frontendDir, "public", "manifest.xml");

fs.copyFileSync(sourceManifest, publicManifest);
console.log("Production manifest copied to frontend/public/manifest.xml");
