import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const [command, gatewayDirectoryArg, inputArg, outputArg] = process.argv.slice(2);
if (!command || !gatewayDirectoryArg || !inputArg || !outputArg) {
  throw new Error("Use: gateway-action.mjs propose|get GATEWAY_DIR INPUT OUTPUT");
}
const gatewayDirectory = resolve(gatewayDirectoryArg);
const config = JSON.parse(await readFile(resolve(gatewayDirectory, "gateway.json"), "utf8"));
const secrets = JSON.parse(await readFile(resolve(gatewayDirectory, "secrets.json"), "utf8"));
if (typeof secrets.gatewayToken !== "string" || secrets.gatewayToken.length < 32) throw new Error("Gateway token unavailable.");

async function request(path, init = {}) {
  const response = await fetch(`http://${config.host}:${config.port}${path}`, {
    ...init,
    headers: { authorization: `Bearer ${secrets.gatewayToken}`, "content-type": "application/json", ...(init.headers ?? {}) },
    signal: AbortSignal.timeout(20_000),
  });
  const value = await response.json().catch(() => ({}));
  return { httpStatus: response.status, value };
}

let result;
if (command === "propose") {
  const proposal = JSON.parse(await readFile(resolve(inputArg), "utf8"));
  result = await request("/v1/actions", { method: "POST", body: JSON.stringify({ proposal, idempotencyKey: proposal.externalId }) });
} else if (command === "get") {
  const created = JSON.parse(await readFile(resolve(inputArg), "utf8"));
  const id = created.value?.id ?? created.value?.action?.id;
  if (!id) throw new Error("Created action id unavailable.");
  result = await request(`/v1/actions/${encodeURIComponent(id)}`);
} else {
  throw new Error("Unknown command.");
}
await writeFile(resolve(outputArg), `${JSON.stringify(result, null, 2)}\n`, { mode: 0o600 });
console.log(JSON.stringify({ httpStatus: result.httpStatus, actionId: result.value?.id ?? result.value?.action?.id, status: result.value?.status ?? result.value?.action?.status }));
if (result.httpStatus >= 400) process.exitCode = 1;
