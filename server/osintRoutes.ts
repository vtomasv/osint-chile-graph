import type { Express } from "express";
import { createHash } from "node:crypto";
import dns from "node:dns/promises";

const MERCADO_PUBLICO_SUPPLIER_ENDPOINT = "https://api.mercadopublico.cl/servicios/v1/Publico/Empresas/BuscarProveedor";
const MERCADO_PUBLICO_PUBLIC_TICKET = "F8537A18-6766-4DEF-9E59-426B4FEE2844";
const REQUEST_TIMEOUT_MS = 4_000;
const USER_AGENT = "OSINT-Chile-Graph/0.4 (+responsible-public-osint; passive-evidence)";

type TransformDefinition = {
  id: string;
  name: string;
  description: string;
  input_types: string[];
  output_types: string[];
  execution_mode: "automatic" | "human_in_the_loop" | "blocked";
  risk_level: "low" | "medium" | "high";
  requires_human: boolean;
  source_policy: string;
};

type GraphNode = {
  id: string;
  type: string;
  label: string;
  value: string;
  properties: Record<string, unknown>;
  confidence: number;
};

type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
  confidence: number;
};

type EvidenceItem = {
  id: string;
  source_name: string;
  source_url: string;
  extract: string;
  confidence: number;
  properties: Record<string, unknown>;
  evidence_kind: string;
  is_verified_osint: boolean;
  created_at: string;
};

type SourceStatusItem = {
  source: string;
  status: "verified_evidence" | "operator_required" | "blocked_or_unavailable" | "no_results" | "error" | "local_algorithm";
  query?: string;
  url?: string;
  message?: string;
  reason?: string;
  checked_at?: string;
  created_at?: string;
  transform_id?: string;
  run_id?: string;
  input_type?: string;
  input_value?: string;
};

type TransformRunItem = {
  id: string;
  transform_id: string;
  input_type: string;
  input_value: string;
  created_at: string;
  output_summary: { entities: number; human_tasks: number; relationships: number };
};

type InvestigationState = {
  investigation: { id: string; title: string; objective: string; status: string; created_at: string };
  nodes: GraphNode[];
  edges: GraphEdge[];
  evidence: EvidenceItem[];
  sourceStatuses: SourceStatusItem[];
  runs: TransformRunItem[];
};

type ConnectorResult = {
  entities: GraphNode[];
  evidence: Array<Omit<EvidenceItem, "id" | "created_at">>;
  source_statuses: SourceStatusItem[];
};

const TRANSFORMS: TransformDefinition[] = [
  {
    id: "cl.rut.dorks",
    name: "RUT → fuentes chilenas reales",
    description: "Consulta Mercado Público por API oficial y crea HITL trazable para SII, Rutificador, Volante o Maleta y Diario Oficial cuando requieren operador.",
    input_types: ["rut"],
    output_types: ["WebEvidence", "Evidence", "SourceStatus", "HumanTask"],
    execution_mode: "automatic",
    risk_level: "low",
    requires_human: false,
    source_policy: "public_api_plus_operator_required_sources",
  },
  { id: "cl.rut.normalize", name: "Normalizar y validar RUT", description: "Valida dígito verificador y genera formato canónico. No se presenta como evidencia OSINT.", input_types: ["rut"], output_types: ["Identifier"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "local_algorithm" },
  { id: "cl.rut.variants", name: "Variantes de búsqueda RUT", description: "Genera variantes útiles para consulta humana; no crea hallazgos sin evidencia externa.", input_types: ["rut"], output_types: ["IdentifierVariant"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "local_algorithm" },
  { id: "cl.rut.public_records.human", name: "RUT en SII/Rutificador/Volante y Maleta HITL", description: "Abre tareas manuales para fuentes que no deben automatizarse sin interacción, autorización o revisión de términos.", input_types: ["rut"], output_types: ["HumanTask"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.rut.business_links.human", name: "Vínculos societarios por RUT HITL", description: "Prepara contraste manual en Diario Oficial, Mercado Público, Registro de Empresas y documentos públicos.", input_types: ["rut"], output_types: ["HumanTask"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.email.analyze", name: "Email → DNS y dominio real", description: "Normaliza email y consulta DNS MX/A del dominio como evidencia técnica real, separada de titularidad personal.", input_types: ["email"], output_types: ["Email", "Domain", "Evidence", "SourceStatus"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "dns_public_records" },
  { id: "cl.email.dorks", name: "Email → búsqueda HITL/API", description: "No scrapea buscadores sin API estable; genera continuidad HITL con URL de consulta y captura de evidencia.", input_types: ["email"], output_types: ["HumanTask", "SourceStatus"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.phone.normalize", name: "Normalizar teléfono chileno", description: "Normaliza a E.164 y clasifica forma; carrier, mensajería o caller ID quedan HITL.", input_types: ["phone"], output_types: ["Phone", "HumanTask", "SourceStatus"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "local_algorithm_plus_hitl" },
  { id: "cl.phone.dorks", name: "Teléfono → fuentes públicas HITL", description: "Prepara búsqueda manual y captura de evidencia; no llama, no envía mensajes y no consulta servicios cerrados automáticamente.", input_types: ["phone"], output_types: ["HumanTask", "SourceStatus"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.phone.messaging.human", name: "Verificación mensajería HITL", description: "Tarea de revisión no intrusiva de canales permitidos; requiere operador.", input_types: ["phone"], output_types: ["HumanTask"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.phone.carrier.human", name: "Carrier/portabilidad autorizada HITL", description: "Consulta de operador o portabilidad sólo mediante fuente autorizada y captura humana.", input_types: ["phone"], output_types: ["HumanTask"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.plate.normalize", name: "Normalizar patente chilena", description: "Valida formatos frecuentes de patente; registros vehiculares quedan HITL autorizado.", input_types: ["plate"], output_types: ["Vehicle", "SourceStatus"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "local_algorithm_plus_hitl" },
  { id: "cl.plate.dorks", name: "Patente → fuentes públicas HITL", description: "Prepara revisión manual de Registro Civil, SERNAC y publicaciones; no automatiza trámites, pagos ni CAPTCHA.", input_types: ["plate"], output_types: ["HumanTask", "SourceStatus"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.plate.vehicle_records.human", name: "Patente → Registro Civil HITL", description: "Consulta manual de certificados/anotaciones si existe autorización; no se automatizan pagos ni trámites.", input_types: ["plate"], output_types: ["HumanTask"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.domain.analyze", name: "Dominio → DNS/HTTP/NIC real", description: "Consulta DNS público, prueba web pasiva y prepara NIC Chile si corresponde.", input_types: ["domain"], output_types: ["Domain", "WebArtifact", "Evidence", "SourceStatus"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "dns_http_public_records" },
  { id: "cl.domain.dorks", name: "Dominio → búsqueda HITL/API", description: "Crea tareas verificables para búsquedas públicas si no hay API de búsqueda configurada.", input_types: ["domain"], output_types: ["HumanTask", "SourceStatus"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.name.variants", name: "Nombre → fuentes públicas HITL", description: "Genera tareas de revisión en fuentes profesionales, Diario Oficial y buscadores; no crea persona sin evidencia.", input_types: ["name"], output_types: ["HumanTask", "SourceStatus"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.company.variants", name: "Empresa → normalización y fuentes HITL", description: "Normaliza razón social y abre fuentes públicas; no infiere vínculos sin evidencia capturada.", input_types: ["company"], output_types: ["Company", "HumanTask", "SourceStatus"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "local_algorithm_plus_hitl" },
  { id: "cl.company.public_records.human", name: "Empresa en fuentes públicas HITL", description: "Prepara búsquedas autorizadas en Diario Oficial, Mercado Público y Registro de Empresas.", input_types: ["company"], output_types: ["HumanTask"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
  { id: "cl.dork.generate", name: "Búsqueda pública verificable genérica", description: "Sin API de búsqueda estable, genera tareas HITL y estados de fuente en lugar de registrar dorks como hallazgos.", input_types: ["rut", "email", "phone", "plate", "name", "company", "domain"], output_types: ["HumanTask", "SourceStatus"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "manual_authorized" },
];

const investigations = new Map<string, InvestigationState>();

function nowIso() {
  return new Date().toISOString();
}

function hashId(prefix: string, ...parts: string[]) {
  return `${prefix}:${createHash("sha1").update(parts.join("|")).digest("hex").slice(0, 14)}`;
}

function getState(investigationId = "demo") {
  const existing = investigations.get(investigationId);
  if (existing) return existing;
  const state: InvestigationState = {
    investigation: {
      id: investigationId,
      title: investigationId === "demo" ? "Expediente OSINT Chile" : `Expediente ${investigationId}`,
      objective: "Recolectar únicamente evidencia verificable desde conectores autorizados o capturas humanas documentadas; no se generan datos ficticios.",
      status: "active",
      created_at: nowIso(),
    },
    nodes: [],
    edges: [],
    evidence: [],
    sourceStatuses: [],
    runs: [],
  };
  investigations.set(investigationId, state);
  return state;
}

function addNode(state: InvestigationState, node: Omit<GraphNode, "id"> & { id?: string }) {
  const id = node.id || hashId("node", node.type, node.value || node.label);
  const existing = state.nodes.find(item => item.id === id);
  if (existing) {
    existing.properties = { ...existing.properties, ...node.properties };
    existing.confidence = Math.max(existing.confidence, node.confidence);
    return existing;
  }
  const created = { ...node, id };
  state.nodes.push(created);
  return created;
}

function addEdge(state: InvestigationState, edge: Omit<GraphEdge, "id"> & { id?: string }) {
  const id = edge.id || hashId("edge", edge.source, edge.target, edge.type);
  const existing = state.edges.find(item => item.id === id);
  if (existing) return existing;
  const created = { ...edge, id };
  state.edges.push(created);
  return created;
}

function addEvidence(state: InvestigationState, evidence: Omit<EvidenceItem, "id" | "created_at">) {
  const created: EvidenceItem = {
    ...evidence,
    id: hashId("evidence", evidence.source_name, evidence.source_url, evidence.extract, nowIso()),
    created_at: nowIso(),
  };
  state.evidence.push(created);
  return created;
}

function addSourceStatus(state: InvestigationState, status: SourceStatusItem, run: TransformRunItem) {
  state.sourceStatuses.push({
    ...status,
    created_at: nowIso(),
    transform_id: run.transform_id,
    run_id: run.id,
    input_type: run.input_type,
    input_value: run.input_value,
  });
}

function cleanRut(value: string) {
  return value.replace(/[^0-9kK]/g, "").toUpperCase();
}

function formatRut(value: string) {
  const cleaned = cleanRut(value);
  if (cleaned.length < 2) return value.trim();
  const body = cleaned.slice(0, -1);
  const dv = cleaned.slice(-1);
  return `${Number(body).toLocaleString("es-CL")}-${dv}`;
}

function validateRut(value: string) {
  const cleaned = cleanRut(value);
  if (cleaned.length < 2) {
    return { valid: false, normalized: value, reason: "RUT demasiado corto", body: "", dv: "" };
  }
  const body = cleaned.slice(0, -1);
  const dv = cleaned.slice(-1);
  let factor = 2;
  let total = 0;
  for (const digit of body.split("").reverse()) {
    if (!/\d/.test(digit)) return { valid: false, normalized: value, reason: "Cuerpo contiene caracteres inválidos", body, dv };
    total += Number(digit) * factor;
    factor = factor === 7 ? 2 : factor + 1;
  }
  const remainder = 11 - (total % 11);
  const expected = remainder === 11 ? "0" : remainder === 10 ? "K" : String(remainder);
  return {
    valid: dv === expected,
    normalized: formatRut(value),
    expected_dv: expected,
    body,
    dv,
    compact: `${body}${dv}`,
    without_points: `${body}-${dv}`,
    risk_note: "Validación matemática local; no confirma identidad ni titularidad.",
  };
}

function normalizePhone(value: string) {
  let digits = value.replace(/\D/g, "");
  if (digits.startsWith("0056")) digits = digits.slice(2);
  let national = digits;
  let e164 = digits ? `+${digits}` : value;
  if (digits.startsWith("56")) {
    national = digits.slice(2);
    e164 = `+${digits}`;
  } else if (digits.startsWith("9") && digits.length === 9) {
    national = digits;
    e164 = `+56${digits}`;
  } else if (digits.length === 8) {
    national = `2${digits}`;
    e164 = `+562${digits}`;
  } else if (digits.length === 9 && digits.startsWith("2")) {
    national = digits;
    e164 = `+56${digits}`;
  }
  const category = national.startsWith("9") && national.length === 9 ? "mobile" : national.startsWith("2") && national.length === 9 ? "landline_rm" : "unknown";
  return { normalized: e164, national, country: e164.startsWith("+56") ? "CL" : "unknown", category, valid_shape: e164.startsWith("+56") && e164.replace(/\D/g, "").length === 11 };
}

function normalizePlate(value: string) {
  const normalized = value.toUpperCase().replace(/[^A-Z0-9]/g, "");
  const modern = /^[A-Z]{4}\d{2}$/.test(normalized);
  const old = /^[A-Z]{2}\d{4}$/.test(normalized);
  return {
    normalized,
    valid_shape: modern || old,
    format: modern ? "modern_abcd12" : old ? "legacy_ab1234" : "unknown_or_requires_review",
    risk_note: "Validación morfológica local; antecedentes vehiculares requieren canal autorizado.",
  };
}

function normalizeEmail(value: string) {
  const email = value.trim().toLowerCase();
  const valid = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
  const [localPart = email, domain = ""] = email.includes("@") ? email.split("@", 2) : [email, ""];
  return { email, valid, local_part: localPart, domain, tld: domain.split(".").pop() || "", is_cl: domain.endsWith(".cl") };
}

function normalizeDomain(value: string) {
  return value.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
}

function searchUrl(query: string) {
  return `https://www.google.com/search?q=${encodeURIComponent(query)}`;
}

function status(source: string, statusValue: SourceStatusItem["status"], query: string, message: string, url = searchUrl(query)): SourceStatusItem {
  return { source, status: statusValue, query, message, url, checked_at: nowIso() };
}

function humanTaskEntity(source: string, value: string, purpose: string, url: string, reason?: string): Omit<GraphNode, "id"> {
  return {
    type: "HumanTask",
    label: `${source}: ${value}`,
    value,
    confidence: 0.35,
    properties: {
      source,
      source_url: url,
      search_url: url,
      status: "pending_manual_review",
      purpose,
      reason: reason || "La fuente requiere interacción humana, CAPTCHA, sesión, aceptación de términos, pago, autorización específica o revisión legal antes de consultar.",
      execution_policy: "operator_required",
      instructions: "Abrir la fuente, revisar términos aplicables, ejecutar la consulta sólo si existe autorización y guardar evidencia con URL, fecha, extracto textual, confianza y entidades observadas.",
      expected_evidence: ["URL o nombre de fuente", "fecha/hora de consulta", "extracto textual", "entidades observadas", "captura o referencia documental si procede"],
    },
  };
}

function addHumanTask(state: InvestigationState, seed: GraphNode | undefined, source: string, value: string, purpose: string, url: string, reason?: string) {
  const task = addNode(state, { ...humanTaskEntity(source, value, purpose, url, reason), id: hashId("task", source, value, purpose) });
  if (seed) addEdge(state, { source: seed.id, target: task.id, type: "REQUIRES_HUMAN", properties: { source, purpose }, confidence: 0.42 });
  return task;
}

async function fetchJson(url: string) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal, headers: { "User-Agent": USER_AGENT, Accept: "application/json,text/plain,*/*" } });
    const text = await response.text();
    try {
      return { response, payload: JSON.parse(text) as unknown, text };
    } catch {
      return { response, payload: null, text };
    }
  } finally {
    clearTimeout(timeout);
  }
}

async function mercadoPublicoSupplierByRut(value: string): Promise<ConnectorResult> {
  const rut = formatRut(value);
  const apiUrl = `${MERCADO_PUBLICO_SUPPLIER_ENDPOINT}?rutempresaproveedor=${encodeURIComponent(rut)}&ticket=${encodeURIComponent(MERCADO_PUBLICO_PUBLIC_TICKET)}`;
  const source = "Mercado Público API BuscarProveedor";
  try {
    const { response, payload, text } = await fetchJson(apiUrl);
    const dict = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
    const companies = Array.isArray(dict.listaEmpresas) ? dict.listaEmpresas as Array<Record<string, unknown>> : [];
    if (response.status === 200 && companies.length > 0) {
      const entities: GraphNode[] = [];
      const evidence: Array<Omit<EvidenceItem, "id" | "created_at">> = [];
      const names: string[] = [];
      companies.forEach((item, index) => {
        const name = String(item.NombreEmpresa || "Proveedor Mercado Público").trim();
        const code = String(item.CodigoEmpresa || "").trim();
        names.push(name);
        evidence.push({
          source_name: source,
          source_url: "https://www.mercadopublico.cl/Home/BusquedaProveedor",
          extract: `La API oficial de Mercado Público devolvió el proveedor ${name} para el RUT ${rut}. CódigoEmpresa=${code || "sin código expuesto"}.`,
          confidence: 0.86,
          evidence_kind: "verified_evidence",
          is_verified_osint: true,
          properties: { connector: "mercado_publico_supplier_api", api_url: apiUrl, rut_query: rut, company_name: name, company_code: code, rank: index + 1, raw_item: item, checked_at: nowIso() },
        });
        entities.push({ id: hashId("node", "Company", name, code), type: "Company", label: name, value: code || name, confidence: 0.86, properties: { evidence_kind: "verified_evidence", source_name: source, source_url: "https://www.mercadopublico.cl/Home/BusquedaProveedor", rut_query: rut, company_code: code } });
      });
      return { entities, evidence, source_statuses: [status(source, "verified_evidence", rut, `Mercado Público devolvió ${companies.length} proveedor(es): ${names.slice(0, 3).join(", ")}.`, "https://www.mercadopublico.cl/Home/BusquedaProveedor")] };
    }
    const message = String(dict.Mensaje || text.slice(0, 240) || "sin resultados parseables");
    const statusValue = response.status === 200 || message.toLowerCase().includes("no hay") ? "no_results" : "blocked_or_unavailable";
    return { entities: [], evidence: [], source_statuses: [status(source, statusValue, rut, `Mercado Público respondió HTTP ${response.status}: ${message}.`, "https://www.mercadopublico.cl/Home/BusquedaProveedor")] };
  } catch (error) {
    return { entities: [], evidence: [], source_statuses: [status(source, "blocked_or_unavailable", rut, `No se pudo consultar Mercado Público: ${(error as Error).name}: ${(error as Error).message}.`, "https://www.mercadopublico.cl/Home/BusquedaProveedor")] };
  }
}

async function dnsEvidenceForDomain(domain: string): Promise<ConnectorResult> {
  const entities: GraphNode[] = [];
  const evidence: Array<Omit<EvidenceItem, "id" | "created_at">> = [];
  const sourceStatuses: SourceStatusItem[] = [];
  const clean = normalizeDomain(domain);
  try {
    const [mx, addresses] = await Promise.allSettled([dns.resolveMx(clean), dns.resolve4(clean)]);
    const mxRecords = mx.status === "fulfilled" ? mx.value : [];
    const aRecords = addresses.status === "fulfilled" ? addresses.value : [];
    entities.push({ id: hashId("node", "Domain", clean), type: "Domain", label: clean, value: clean, confidence: 0.78, properties: { mx_records: mxRecords, a_records: aRecords, is_cl: clean.endsWith(".cl") } });
    if (mxRecords.length || aRecords.length) {
      evidence.push({ source_name: "DNS público", source_url: `dns://${clean}`, extract: `Consulta DNS pública para ${clean}: MX=${mxRecords.map(r => `${r.exchange}:${r.priority}`).join(", ") || "sin MX"}; A=${aRecords.join(", ") || "sin A"}.`, confidence: 0.82, evidence_kind: "verified_evidence", is_verified_osint: true, properties: { connector: "node_dns", domain: clean, mx_records: mxRecords, a_records: aRecords, checked_at: nowIso() } });
      sourceStatuses.push(status("DNS público", "verified_evidence", clean, "Se obtuvieron registros DNS públicos verificables.", `dns://${clean}`));
    } else {
      sourceStatuses.push(status("DNS público", "no_results", clean, "La consulta DNS respondió sin registros MX/A útiles.", `dns://${clean}`));
    }
  } catch (error) {
    sourceStatuses.push(status("DNS público", "blocked_or_unavailable", clean, `No se pudo resolver DNS: ${(error as Error).message}.`, `dns://${clean}`));
  }
  if (clean.endsWith(".cl")) {
    sourceStatuses.push(status("NIC Chile Whois", "operator_required", clean, "NIC Chile requiere revisión manual en su formulario público; se deja como HITL para capturar evidencia si procede.", `https://www.nic.cl/whois/?dominio=${encodeURIComponent(clean)}`));
  }
  return { entities, evidence, source_statuses: sourceStatuses };
}

function nearestSeed(state: InvestigationState, inputType: string, inputValue: string) {
  return state.nodes.find(node => node.type === "Seed" && node.properties.input_type === inputType && node.value === inputValue) || state.nodes.find(node => node.value === inputValue);
}

async function executeTransform(state: InvestigationState, run: TransformRunItem) {
  const { input_type: inputType, input_value: inputValue, transform_id: transformId } = run;
  let seed = nearestSeed(state, inputType, inputValue);
  if (!seed) seed = addNode(state, { type: "Seed", label: inputValue, value: inputValue, confidence: 0.5, properties: { input_type: inputType } });
  const createdEntities: GraphNode[] = [];
  const createdTaskIds = new Set<string>();

  const createAndLink = (node: Omit<GraphNode, "id"> & { id?: string }, relation = "DERIVED_FROM") => {
    const created = addNode(state, node);
    createdEntities.push(created);
    addEdge(state, { source: seed.id, target: created.id, type: relation, properties: { transform_id: transformId, run_id: run.id }, confidence: created.confidence });
    return created;
  };

  const recordConnector = (result: ConnectorResult) => {
    result.entities.forEach(entity => createAndLink(entity, entity.type === "Company" ? "FOUND_IN_SOURCE" : "DERIVED_FROM_SOURCE"));
    result.evidence.forEach(item => {
      const ev = addEvidence(state, item);
      const evidenceNode = createAndLink({ type: "WebEvidence", label: String(item.properties.title || item.source_name), value: item.source_url || item.source_name, confidence: item.confidence, properties: { ...item.properties, extract: item.extract, source_url: item.source_url, evidence_id: ev.id } }, "SUPPORTED_BY_EVIDENCE");
      addEdge(state, { source: evidenceNode.id, target: seed.id, type: "EVIDENCE_FOR", properties: { source_name: item.source_name, evidence_id: ev.id }, confidence: item.confidence });
    });
    result.source_statuses.forEach(item => addSourceStatus(state, item, run));
  };

  if (transformId === "cl.rut.dorks") {
    const rut = validateRut(inputValue);
    createAndLink({ type: "Rut", label: String(rut.normalized), value: String(rut.compact || cleanRut(inputValue)), confidence: rut.valid ? 0.7 : 0.4, properties: { ...rut, evidence_kind: "local_algorithm" } }, "NORMALIZED_AS");
    recordConnector(await mercadoPublicoSupplierByRut(inputValue));
    const tasks = [
      addHumanTask(state, seed, "SII situación tributaria", String(rut.normalized), "Consultar manualmente situación tributaria/RUT en el SII si existe base legítima y respetando CAPTCHA/términos.", "https://zeus.sii.cl/cvc/stc/stc.html"),
      addHumanTask(state, seed, "Rutificador", String(rut.normalized), "Revisar manualmente si la fuente es legalmente utilizable y capturar evidencia sólo si corresponde.", `https://www.google.com/search?q=${encodeURIComponent(`rutificador ${rut.normalized}`)}`),
      addHumanTask(state, seed, "Volante o Maleta", String(rut.normalized), "Revisar manualmente menciones públicas asociadas; no automatizar fuentes con controles o restricciones.", `https://www.google.com/search?q=${encodeURIComponent(`"${rut.normalized}" "volante o maleta"`)}`),
      addHumanTask(state, seed, "Diario Oficial", String(rut.normalized), "Buscar publicaciones públicas del Diario Oficial asociadas al RUT o razón social relacionada.", `https://www.diariooficial.interior.gob.cl/edicionelectronica/index.php?date=${new Date().toISOString().slice(0, 10)}`),
    ];
    tasks.forEach(task => createdTaskIds.add(task.id));
    tasks.forEach(task => addSourceStatus(state, status(String(task.properties.source), "operator_required", String(rut.normalized), String(task.properties.reason), String(task.properties.search_url)), run));
  } else if (transformId === "cl.rut.normalize" || transformId === "cl.rut.variants") {
    const rut = validateRut(inputValue);
    createAndLink({ type: transformId.endsWith("variants") ? "IdentifierVariant" : "Rut", label: String(rut.normalized), value: String(rut.compact || cleanRut(inputValue)), confidence: rut.valid ? 0.64 : 0.35, properties: { ...rut, variants: [rut.normalized, rut.without_points, rut.compact].filter(Boolean), evidence_kind: "local_algorithm" } }, "LOCAL_DERIVATION");
    addSourceStatus(state, status("Algoritmo local RUT", "local_algorithm", inputValue, "Sólo se validó el dígito verificador. No es evidencia OSINT ni confirma titularidad.", "about:blank"), run);
  } else if (transformId.includes("rut") && transformId.includes("human")) {
    const rut = validateRut(inputValue);
    [
      ["SII", "https://zeus.sii.cl/cvc/stc/stc.html", "Consultar manualmente SII si hay autorización y registrar extracto verificable."],
      ["Diario Oficial", `https://www.google.com/search?q=${encodeURIComponent(`site:diariooficial.interior.gob.cl "${rut.normalized}"`)}`, "Buscar publicaciones públicas asociadas al RUT."],
      ["Registro de Empresas", "https://www.registrodeempresasysociedades.cl/", "Contrastar vínculos societarios mediante canal autorizado."],
      ["Mercado Público", "https://www.mercadopublico.cl/Home/BusquedaProveedor", "Verificar proveedor en interfaz pública si la API no basta."],
    ].forEach(([source, url, purpose]) => {
      const task = addHumanTask(state, seed, source, String(rut.normalized), purpose, url);
      createdTaskIds.add(task.id);
      addSourceStatus(state, status(source, "operator_required", String(rut.normalized), String(task.properties.reason), url), run);
    });
  } else if (transformId === "cl.email.analyze") {
    const email = normalizeEmail(inputValue);
    createAndLink({ type: "Email", label: email.email, value: email.email, confidence: email.valid ? 0.68 : 0.35, properties: { ...email, evidence_kind: "local_algorithm" } }, "NORMALIZED_AS");
    if (email.domain) recordConnector(await dnsEvidenceForDomain(email.domain));
  } else if (inputType === "domain" && transformId === "cl.domain.analyze") {
    recordConnector(await dnsEvidenceForDomain(inputValue));
  } else if (inputType === "phone" && transformId === "cl.phone.normalize") {
    const phone = normalizePhone(inputValue);
    createAndLink({ type: "Phone", label: phone.normalized, value: phone.normalized, confidence: phone.valid_shape ? 0.62 : 0.3, properties: { ...phone, evidence_kind: "local_algorithm" } }, "NORMALIZED_AS");
    addSourceStatus(state, status("Algoritmo local teléfono", "local_algorithm", inputValue, "Sólo se normalizó el número. Carrier, titularidad y mensajería requieren fuente autorizada o HITL.", "about:blank"), run);
    const task = addHumanTask(state, seed, "Subtel/portabilidad/caller ID autorizado", phone.normalized, "Verificar operador o menciones públicas sólo mediante fuentes autorizadas y sin contacto automatizado.", searchUrl(`"${phone.normalized}" Chile teléfono`));
    createdTaskIds.add(task.id);
  } else if (inputType === "plate" && transformId === "cl.plate.normalize") {
    const plate = normalizePlate(inputValue);
    createAndLink({ type: "Vehicle", label: plate.normalized, value: plate.normalized, confidence: plate.valid_shape ? 0.62 : 0.28, properties: { ...plate, evidence_kind: "local_algorithm" } }, "NORMALIZED_AS");
    addSourceStatus(state, status("Algoritmo local patente", "local_algorithm", inputValue, "Sólo se validó el formato. Antecedentes vehiculares requieren canal autorizado o captura humana.", "about:blank"), run);
    const task = addHumanTask(state, seed, "Registro Civil / certificados vehiculares", plate.normalized, "Consultar certificados/anotaciones sólo por canal autorizado y con base legítima.", "https://www.registrocivil.cl/", "La fuente puede requerir pago, sesión, CAPTCHA o autorización específica; no se automatiza.");
    createdTaskIds.add(task.id);
  } else if (inputType === "company" && (transformId === "cl.company.variants" || transformId.includes("company"))) {
    const company = inputValue.trim().replace(/\s+/g, " ");
    createAndLink({ type: "Company", label: company, value: company, confidence: 0.55, properties: { normalized: company.toUpperCase(), evidence_kind: "local_algorithm", risk_note: "Normalización local; no confirma existencia legal." } }, "NORMALIZED_AS");
    ["Diario Oficial", "Mercado Público", "Registro de Empresas"].forEach(source => {
      const url = source === "Registro de Empresas" ? "https://www.registrodeempresasysociedades.cl/" : searchUrl(`"${company}" Chile ${source}`);
      const task = addHumanTask(state, seed, source, company, `Buscar registros públicos de empresa en ${source} y capturar evidencia verificable.`, url);
      createdTaskIds.add(task.id);
      addSourceStatus(state, status(source, "operator_required", company, String(task.properties.reason), url), run);
    });
  } else {
    const query = inputValue.trim();
    const task = addHumanTask(state, seed, "Búsqueda pública manual/API", query, "Sin API de búsqueda estable configurada, se genera tarea humana para evitar registrar dorks como evidencia.", searchUrl(`"${query}" Chile`));
    createdTaskIds.add(task.id);
    addSourceStatus(state, status("Búsqueda pública manual/API", "operator_required", query, "No se scrapean buscadores ni fuentes restringidas. Complete HITL o configure una API autorizada.", String(task.properties.search_url)), run);
  }

  const createdTasks = state.nodes.filter(node => createdTaskIds.has(node.id));
  const responseEntities = [
    ...createdEntities,
    ...createdTasks.filter(task => !createdEntities.some(entity => entity.id === task.id)),
  ];

  run.output_summary = {
    entities: responseEntities.length,
    human_tasks: createdTasks.length,
    relationships: state.edges.filter(edge => edge.properties.run_id === run.id).length,
  };
  return responseEntities;
}

function buildFindings(state: InvestigationState) {
  const evidence = state.evidence;
  const verifiedEvidence = evidence.filter(item => item.is_verified_osint || item.evidence_kind === "verified_evidence");
  const humanTasks = state.nodes.filter(node => node.type === "HumanTask");
  const relationships = state.edges.map(edge => {
    const source = state.nodes.find(node => node.id === edge.source);
    const target = state.nodes.find(node => node.id === edge.target);
    return { ...edge, source_id: edge.source, target_id: edge.target, source_label: source?.label || edge.source, target_label: target?.label || edge.target, source_type: source?.type, target_type: target?.type };
  });
  const entityTypes = state.nodes.reduce<Record<string, number>>((acc, node) => ({ ...acc, [node.type]: (acc[node.type] || 0) + 1 }), {});
  const evidenceBySource = verifiedEvidence.reduce<Record<string, number>>((acc, item) => ({ ...acc, [item.source_name]: (acc[item.source_name] || 0) + 1 }), {});
  const averageConfidence = state.nodes.length ? state.nodes.reduce((sum, node) => sum + node.confidence, 0) / state.nodes.length : 0;
  const profiles = state.nodes.filter(node => node.type !== "HumanTask").map(node => {
    const directRels = relationships.filter(rel => rel.source_id === node.id || rel.target_id === node.id);
    const directEvidence = evidence.filter(item => JSON.stringify(item.properties).includes(node.value) || directRels.some(rel => String(rel.properties.evidence_id || "") === item.id));
    return {
      entity: node,
      analysis: {
        title: node.label,
        summary: directEvidence.length ? `${node.label} tiene ${directEvidence.length} evidencia(s) asociada(s) desde fuentes reales o captura humana.` : `${node.label} sólo tiene derivaciones locales o tareas pendientes; no se afirma hallazgo OSINT sin evidencia.`,
        facts: directEvidence.map(item => item.extract).slice(0, 5),
        gaps: directEvidence.length ? [] : ["Falta evidencia externa verificable o captura HITL."],
        next_steps: ["Revisar pestaña Fuentes/HITL y completar sólo fuentes autorizadas."],
        mode: "evidence_first",
      },
      relationships: directRels,
      evidence: directEvidence,
      stats: { relationships: directRels.length, evidence: directEvidence.length, human_tasks: directRels.filter(rel => rel.target_type === "HumanTask" || rel.source_type === "HumanTask").length, confidence: node.confidence },
    };
  });
  return {
    investigation: state.investigation,
    summary: { entities: state.nodes.length, relationships: state.edges.length, evidence: verifiedEvidence.length, evidence_total_records: evidence.length, source_statuses: state.sourceStatuses.length, human_tasks: humanTasks.length, pending_human_tasks: humanTasks.filter(task => task.properties.status !== "completed").length, transform_runs: state.runs.length, average_confidence: averageConfidence, entity_types: entityTypes, evidence_by_source: evidenceBySource },
    analysis: {
      mode: "real_osint_no_synthetic_findings",
      executive_summary: verifiedEvidence.length ? `El expediente contiene ${verifiedEvidence.length} evidencia(s) verificable(s). Las fuentes restringidas quedan como tareas HITL y no como datos inventados.` : "No hay evidencia OSINT verificada todavía. El sistema muestra estados de fuente y tareas HITL en vez de fabricar hallazgos.",
      key_findings: verifiedEvidence.length ? verifiedEvidence.map(item => item.extract).slice(0, 6) : ["Sin evidencia OSINT real registrada en esta sesión."],
      gaps: ["Las fuentes con CAPTCHA, sesión, pago o restricciones requieren operador y autorización.", "Los algoritmos locales sólo normalizan identificadores; no prueban identidad ni titularidad."],
      recommended_next_steps: ["Ejecutar transforms de fuentes reales para el tipo de semilla.", "Completar tareas HITL con URL, fecha, extracto y entidades observadas.", "Configurar API de búsqueda autorizada si se requiere automatizar web search de forma estable."],
      entity_type_distribution: entityTypes,
      ai_status: "Síntesis local basada en evidencias y estados de fuente; no usa datos simulados.",
    },
    entities: state.nodes,
    entity_profiles: profiles,
    relationships,
    evidence,
    source_statuses: state.sourceStatuses,
    human_tasks: humanTasks,
    runs: state.runs,
    timeline: [
      ...state.runs.map(run => ({ at: run.created_at, kind: "transform_run", title: run.transform_id, detail: `${run.input_type}=${run.input_value}`, confidence: 0.7 })),
      ...state.sourceStatuses.map(item => ({ at: item.created_at || item.checked_at || nowIso(), kind: "source_status", title: `${item.source}: ${item.status}`, detail: item.message || item.reason || "Estado de fuente registrado.", confidence: item.status === "verified_evidence" ? 0.8 : 0.35 })),
      ...evidence.map(item => ({ at: item.created_at, kind: "evidence", title: item.source_name, detail: item.extract, confidence: item.confidence })),
    ].sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime()),
    visualizations: {
      treemap: Object.entries(entityTypes).map(([name, size]) => ({ name, size })),
      sankey: { nodes: state.runs.map(run => ({ name: run.transform_id })).concat(verifiedEvidence.map(item => ({ name: item.source_name }))), links: [] },
      semantic_clusters: Object.entries(evidenceBySource).map(([name, count]) => ({ name, count, avg_confidence: 0.75, examples: [] })),
    },
  };
}

export function registerOsintRoutes(app: Express) {
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", ai_provider: "local-evidence-first", ollama_base_url: "disabled" });
  });

  app.get("/api/investigations", (_req, res) => {
    res.json(Array.from(investigations.values()).map(item => item.investigation));
  });

  app.get("/api/transforms", (_req, res) => {
    res.json(TRANSFORMS);
  });

  app.post("/api/seeds", (req, res) => {
    const investigationId = String(req.body?.investigation_id || "demo");
    const inputType = String(req.body?.input_type || "unknown");
    const value = String(req.body?.value || "").trim();
    if (!value) return res.status(400).json({ error: "value is required" });
    const state = getState(investigationId);
    const node = addNode(state, { id: hashId("seed", inputType, value), type: "Seed", label: value, value, confidence: 0.55, properties: { input_type: inputType, created_by: "operator", evidence_kind: "seed" } });
    res.json(node);
  });

  app.post("/api/transforms/run", async (req, res) => {
    try {
      const investigationId = String(req.body?.investigation_id || "demo");
      const transformId = String(req.body?.transform_id || "");
      const inputType = String(req.body?.input_type || "");
      const value = String(req.body?.value || "").trim();
      if (!transformId || !inputType || !value) return res.status(400).json({ error: "transform_id, input_type and value are required" });
      const transform = TRANSFORMS.find(item => item.id === transformId);
      if (!transform) return res.status(404).json({ error: `Unknown transform ${transformId}` });
      const state = getState(investigationId);
      const run: TransformRunItem = { id: hashId("run", transformId, inputType, value, String(Date.now())), transform_id: transformId, input_type: inputType, input_value: value, created_at: nowIso(), output_summary: { entities: 0, human_tasks: 0, relationships: 0 } };
      state.runs.unshift(run);
      const createdEntities = await executeTransform(state, run);
      res.json({ run_id: run.id, output: { source_statuses: state.sourceStatuses.filter(item => item.run_id === run.id), evidence: state.evidence.filter(item => item.created_at >= run.created_at), output_summary: run.output_summary }, created_entities: createdEntities });
    } catch (error) {
      res.status(500).json({ error: (error as Error).message });
    }
  });

  app.get("/api/graph/:investigationId", (req, res) => {
    const state = getState(req.params.investigationId);
    res.json({ nodes: state.nodes, edges: state.edges });
  });

  app.get("/api/investigations/:investigationId/findings", (req, res) => {
    const state = getState(req.params.investigationId);
    res.json(buildFindings(state));
  });

  app.post("/api/human-tasks/:taskId/complete", (req, res) => {
    const taskId = req.params.taskId;
    const investigationId = String(req.body?.investigation_id || "demo");
    const state = getState(investigationId);
    const task = state.nodes.find(node => node.id === taskId && node.type === "HumanTask");
    if (!task) return res.status(404).json({ error: "Human task not found" });
    const sourceName = String(req.body?.source_name || task.properties.source || "Fuente revisada por operador");
    const sourceUrl = String(req.body?.source_url || task.properties.search_url || "");
    const extract = String(req.body?.extract || "").trim();
    const confidence = Math.max(0, Math.min(1, Number(req.body?.confidence ?? 0.72)));
    const statusValue = String(req.body?.status || "confirmed");
    if (!extract && statusValue === "confirmed") return res.status(400).json({ error: "extract is required for confirmed evidence" });
    task.properties = { ...task.properties, status: statusValue === "confirmed" ? "completed" : statusValue, completed_at: nowIso(), operator_notes: req.body?.notes || "" };
    const evidence = addEvidence(state, { source_name: sourceName, source_url: sourceUrl, extract: extract || `Operador registró estado ${statusValue} sin hallazgo confirmado.`, confidence: statusValue === "confirmed" ? confidence : 0.25, evidence_kind: statusValue === "confirmed" ? "operator_captured_evidence" : "source_status", is_verified_osint: statusValue === "confirmed", properties: { human_task_completed: true, task_id: taskId, source: task.properties.source, status: statusValue, notes: req.body?.notes || "" } });
    const createdEntities: GraphNode[] = [];
    const observed = Array.isArray(req.body?.observed_entities) ? req.body.observed_entities as Array<Record<string, unknown>> : [];
    observed.forEach(item => {
      const label = String(item.label || item.value || "Entidad observada");
      const node = addNode(state, { type: String(item.type || "ObservedEntity"), label, value: String(item.value || label), confidence: Number(item.confidence || confidence), properties: { ...(item.properties || {}), source_name: sourceName, source_url: sourceUrl, evidence_id: evidence.id, captured_from_operator_form: true } as Record<string, unknown> });
      createdEntities.push(node);
      addEdge(state, { source: task.id, target: node.id, type: "CONFIRMED_BY_HUMAN", properties: { evidence_id: evidence.id, source_name: sourceName }, confidence });
    });
    addSourceStatus(state, { source: sourceName, status: statusValue === "confirmed" ? "verified_evidence" : "no_results", query: String(task.value), url: sourceUrl, message: extract || `Operador registró ${statusValue}.`, checked_at: nowIso() }, { id: hashId("manual-run", taskId, nowIso()), transform_id: "human_task.complete", input_type: task.type, input_value: task.value, created_at: nowIso(), output_summary: { entities: createdEntities.length, human_tasks: 0, relationships: createdEntities.length } });
    res.json({ status: "ok", evidence_id: evidence.id, created_entities: createdEntities });
  });

  app.post("/api/ai/run", (req, res) => {
    res.json({ provider: "local", model: "evidence-first-summary", content: `No se invocó un modelo para inventar datos. La solicitud ${String(req.body?.prompt_id || "")} debe operar sobre evidencias, fuentes y tareas HITL ya registradas.` });
  });
}
