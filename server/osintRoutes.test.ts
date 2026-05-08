import express from "express";
import { createServer, type Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { registerOsintRoutes } from "./osintRoutes";

let server: Server;
let baseUrl = "";

beforeAll(async () => {
  const app = express();
  app.use(express.json());
  registerOsintRoutes(app);
  server = createServer(app);
  await new Promise<void>(resolve => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (address && typeof address === "object") {
        baseUrl = `http://127.0.0.1:${address.port}`;
      }
      resolve();
    });
  });
});

afterAll(async () => {
  await new Promise<void>((resolve, reject) => {
    server.close(error => (error ? reject(error) : resolve()));
  });
});

describe("OSINT REST routes", () => {
  it("expone transforms chilenos reales con política de fuente explícita", async () => {
    const response = await fetch(`${baseUrl}/api/transforms`);
    const transforms = (await response.json()) as Array<{ id: string; description: string; source_policy: string; requires_human: boolean }>;

    expect(response.status).toBe(200);
    expect(transforms[0]?.id).toBe("cl.rut.dorks");
    expect(transforms.some(item => item.id === "cl.email.analyze" && item.source_policy === "dns_public_records")).toBe(true);
    expect(transforms.some(item => item.id === "cl.rut.public_records.human" && item.requires_human)).toBe(true);
    expect(transforms.find(item => item.id === "cl.rut.dorks")?.description).toContain("Mercado Público");
  });

  it("genera tareas HITL y estados de fuente sin crear evidencia ficticia", async () => {
    const investigationId = `vitest-${Date.now()}`;
    const seedResponse = await fetch(`${baseUrl}/api/seeds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ investigation_id: investigationId, input_type: "rut", value: "12.345.678-5" }),
    });
    expect(seedResponse.status).toBe(200);

    const runResponse = await fetch(`${baseUrl}/api/transforms/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ investigation_id: investigationId, transform_id: "cl.rut.public_records.human", input_type: "rut", value: "12.345.678-5" }),
    });
    const runPayload = (await runResponse.json()) as { created_entities: Array<{ type: string }>; output: { output_summary: { human_tasks: number } } };

    expect(runResponse.status).toBe(200);
    expect(runPayload.created_entities.some(item => item.type === "HumanTask")).toBe(true);
    expect(runPayload.output.output_summary.human_tasks).toBeGreaterThan(0);

    const findingsResponse = await fetch(`${baseUrl}/api/investigations/${investigationId}/findings`);
    const findings = (await findingsResponse.json()) as {
      summary: { evidence: number; evidence_total_records: number; source_statuses: number; human_tasks: number };
      evidence: Array<{ is_verified_osint?: boolean; evidence_kind?: string }>;
      source_statuses: Array<{ status: string; source: string }>;
      human_tasks: Array<{ properties: { search_url?: string; instructions?: string } }>;
      analysis: { executive_summary: string };
    };

    expect(findingsResponse.status).toBe(200);
    expect(findings.summary.evidence).toBe(0);
    expect(findings.summary.evidence_total_records).toBe(0);
    expect(findings.evidence).toHaveLength(0);
    expect(findings.summary.source_statuses).toBeGreaterThan(0);
    expect(findings.source_statuses.every(item => item.status === "operator_required")).toBe(true);
    expect(findings.summary.human_tasks).toBeGreaterThan(0);
    expect(findings.human_tasks.every(task => typeof task.properties.search_url === "string" && task.properties.search_url.length > 0)).toBe(true);
    expect(findings.human_tasks.every(task => String(task.properties.instructions || "").includes("guardar evidencia"))).toBe(true);
    expect(findings.analysis.executive_summary).toContain("No hay evidencia OSINT verificada");
  });
});
