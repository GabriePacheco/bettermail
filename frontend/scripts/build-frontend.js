import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(scriptDir, "..", "..");
const frontendDir = path.join(rootDir, "frontend");
const distDir = path.join(frontendDir, "dist");
const staticDir = path.join(rootDir, "app", "static");

function removeDir(dir) {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });

  for (const item of fs.readdirSync(src)) {
    const srcPath = path.join(src, item);
    const destPath = path.join(dest, item);

    if (fs.statSync(srcPath).isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

console.log("Generating frontend build...");

execSync("npm run build", {
  cwd: frontendDir,
  stdio: "inherit",
});

console.log("Cleaning app/static...");

removeDir(staticDir);
fs.mkdirSync(staticDir, { recursive: true });

console.log("Copying frontend/dist to app/static...");

copyDir(distDir, staticDir);

const indexPath = path.join(staticDir, "index.html");
const taskpanePath = path.join(staticDir, "taskpane.html");

if (!fs.existsSync(indexPath)) {
  throw new Error("index.html was not found in app/static.");
}

fs.copyFileSync(indexPath, taskpanePath);

console.log("taskpane.html created.");
console.log("Frontend ready in app/static.");
