#!/usr/bin/env node
import { createHash, createPublicKey, verify } from "node:crypto";
import { readFile } from "node:fs/promises";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 2) {
  args.set(process.argv[index], process.argv[index + 1]);
}

const reportPath = args.get("--report");
const publicKeyPath = args.get("--public-key");
if (!reportPath || !publicKeyPath) {
  throw new Error("Use: node verify-boundary-receipt.mjs --report REPORT --public-key PUBLIC_KEY [--manifest MANIFEST --evidence EVIDENCE]");
}

const canonical = (value) => {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Canonical JSON does not support non-finite numbers.");
    return Object.is(value, -0) ? 0 : value;
  }
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().filter((key) => value[key] !== undefined).map((key) => [key, canonical(value[key])]));
  }
  throw new Error(`Canonical JSON does not support ${typeof value}.`);
};

const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const report = JSON.parse(await readFile(reportPath, "utf8"));
const publicKey = createPublicKey(await readFile(publicKeyPath, "utf8"));
const coreBytes = Buffer.from(JSON.stringify(canonical(report.core)));
const checks = [];

checks.push({
  id: "signed_payload_digest",
  pass: sha256(coreBytes) === report.signature?.payloadSha256,
});
checks.push({
  id: "ed25519_signature",
  pass: report.signature?.algorithm === "Ed25519"
    && verify(null, coreBytes, publicKey, Buffer.from(report.signature.signature ?? "", "base64url")),
});

for (const [argument, field, id] of [
  ["--manifest", "manifestSha256", "manifest_binding"],
  ["--evidence", "evidenceSha256", "evidence_binding"],
]) {
  const path = args.get(argument);
  if (path) {
    const document = JSON.parse(await readFile(path, "utf8"));
    const bytes = Buffer.from(JSON.stringify(canonical(document)));
    checks.push({ id, pass: sha256(bytes) === report.core?.[field] });
  }
}

const result = checks.every((check) => check.pass) ? "PASS" : "UNKNOWN";
console.log(JSON.stringify({ result, reportId: report.core?.reportId, checks }, null, 2));
if (result !== "PASS") process.exitCode = 1;
