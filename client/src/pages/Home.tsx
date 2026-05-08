/**
 * Diseño seleccionado: Cartografía forense neo-brutalista chilena.
 * Esta pantalla funciona como expediente operativo: primero lectura analítica por entidad,
 * luego grafo y visualizaciones; los logs quedan como apoyo, no como producto final.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  ClipboardList,
  Copy,
  Database,
  ExternalLink,
  FileText,
  Fingerprint,
  GitBranch,
  Layers3,
  LockKeyhole,
  Network,
  Play,
  RefreshCw,
  Route,
  Search,
  ShieldCheck,
  Split,
  Target,
} from "lucide-react";
import {
  api,
  API_BASE_URL,
  type CompleteHumanTaskPayload,
  type EntityProfile,
  type FindingRelationship,
  type FindingsReport,
  type GraphEdge,
  type GraphNode,
  type HumanTaskItem,
  type Transform,
} from "@/lib/api";
import { Button } from "@/components/ui/button";

const HERO_URL = "https://d2xsxph8kpxj0f.cloudfront.net/116512295/DQkjRB7L57osWitT3YRxBp/osint_chile_hero_map-dBCsW8NcXUuxL7xeZhL6Ds.webp";
const GRAPH_PANEL_URL = "https://d2xsxph8kpxj0f.cloudfront.net/116512295/DQkjRB7L57osWitT3YRxBp/osint_chile_graph_panel-VpJrj7VKA6SgHYwENhokrC.webp";
const HUMAN_LOOP_URL = "https://d2xsxph8kpxj0f.cloudfront.net/116512295/DQkjRB7L57osWitT3YRxBp/osint_chile_human_loop-ShKauUneFyvzmr2KJZnyYq.webp";

const inputTypes = [
  { value: "rut", label: "RUT" },
  { value: "email", label: "Email .cl" },
  { value: "phone", label: "Teléfono" },
  { value: "plate", label: "Patente" },
  { value: "domain", label: "Dominio" },
  { value: "name", label: "Nombre" },
  { value: "company", label: "Empresa" },
];

const findingTabs = [
  { id: "dossier", label: "Expediente" },
  { id: "entities", label: "Fichas" },
  { id: "tasks", label: "HITL operativo" },
  { id: "visual", label: "Visualizaciones" },
  { id: "relationships", label: "Relaciones" },
  { id: "evidence", label: "Evidencias" },
  { id: "runs", label: "Transforms" },
  { id: "timeline", label: "Timeline" },
] as const;

type FindingTab = (typeof findingTabs)[number]["id"];
type IconType = typeof BarChart3;

type HitlDraft = {
  source_name: string;
  source_url: string;
  extract: string;
  confidence: number;
  status: CompleteHumanTaskPayload["status"];
  observed: string;
  notes: string;
};

function nodeColor(type: string) {
  if (type === "HumanTask") return "#d49b4a";
  if (type === "DorkQuery") return "#81a684";
  if (type === "Seed") return "#e6c27a";
  if (type === "Vehicle" || type === "Plate") return "#b76f52";
  if (type === "Phone") return "#6fa8a1";
  if (type === "Domain") return "#9db887";
  if (type === "Rut" || type === "RUT") return "#c7b68b";
  if (type === "Person") return "#d2d0c7";
  return "#d2d0c7";
}

function confidenceTone(confidence = 0) {
  if (confidence >= 0.85) return "border-[#81a684]/50 text-[#9fc7a1]";
  if (confidence >= 0.65) return "border-[#e6c27a]/50 text-[#e6c27a]";
  return "border-[#d49b4a]/50 text-[#d49b4a]";
}

function formatConfidence(confidence?: number) {
  return `${Math.round((confidence || 0) * 100)}%`;
}

function stringifyValue(value: unknown) {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value);
}

function formatProperties(properties: Record<string, unknown>) {
  const entries = Object.entries(properties || {}).filter(([, value]) => value !== undefined && value !== null && value !== "" && value !== false);
  if (!entries.length) return "Sin metadatos registrados";
  return entries
    .slice(0, 10)
    .map(([key, value]) => `${key}: ${stringifyValue(value)}`)
    .join(" · ");
}

function graphLayout(nodes: GraphNode[]) {
  const centerX = 440;
  const centerY = 240;
  const radiusX = 330;
  const radiusY = 175;
  return nodes.map((node, index) => {
    const angle = nodes.length <= 1 ? 0 : (Math.PI * 2 * index) / nodes.length - Math.PI / 2;
    const isSeed = node.type === "Seed";
    return {
      ...node,
      x: isSeed ? centerX : centerX + Math.cos(angle) * radiusX,
      y: isSeed ? centerY : centerY + Math.sin(angle) * radiusY,
    };
  });
}

function parseObservedEntities(text: string) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [type = "ObservedEntity", label = line, value = label] = line.split("|").map((part) => part.trim());
      return { type, label, value, confidence: 0.72, properties: { captured_from_operator_form: true } };
    });
}

const demoNodes: GraphNode[] = [
  { id: "seed-rut-demo", type: "Seed", label: "RUT 12.345.678-5", value: "12.345.678-5", confidence: 0.92, properties: { normalized: "12345678-5", category: "rut" } },
  { id: "person-demo", type: "Person", label: "Persona objetivo", value: "persona-demo", confidence: 0.68, properties: { inferred_from: "RUT", needs_human_confirmation: true } },
  { id: "phone-demo", type: "Phone", label: "+56 9 8765 4321", value: "+56987654321", confidence: 0.71, properties: { format: "E.164 Chile", carrier_pending_hitl: true } },
  { id: "plate-demo", type: "Plate", label: "ABCD12", value: "ABCD12", confidence: 0.63, properties: { format: "patente nueva", vehicle_query_pending: true } },
  { id: "hitl-demo", type: "HumanTask", label: "Consultar fuente autorizada", value: "RUT 12.345.678-5", confidence: 0.5, properties: { source: "Fuente pública/autorizada", search_url: "https://www.google.com/search?q=12.345.678-5", purpose: "Verificar coincidencias y capturar evidencia manual." } },
];

const demoEdges: GraphEdge[] = [
  { id: "e1", source: "seed-rut-demo", target: "person-demo", type: "IDENTIFIES_CANDIDATE", confidence: 0.68, properties: {} },
  { id: "e2", source: "person-demo", target: "phone-demo", type: "POSSIBLE_CONTACT", confidence: 0.61, properties: {} },
  { id: "e3", source: "person-demo", target: "plate-demo", type: "POSSIBLE_VEHICLE", confidence: 0.56, properties: {} },
  { id: "e4", source: "seed-rut-demo", target: "hitl-demo", type: "REQUIRES_HUMAN", confidence: 0.5, properties: {} },
];

function createDemoReport(): FindingsReport {
  return {
    investigation: { id: "demo", title: "Expediente demo — RUT 12.345.678-5", objective: "Vista demostrativa offline. Levanta la API local para persistir datos reales del objetivo.", status: "demo" },
    summary: { entities: demoNodes.length, relationships: demoEdges.length, evidence: 2, human_tasks: 1, pending_human_tasks: 1, transform_runs: 3, average_confidence: 0.69, entity_types: { Seed: 1, Person: 1, Phone: 1, Plate: 1, HumanTask: 1 }, evidence_by_source: { demo: 2 } },
    analysis: { mode: "demo_local", executive_summary: "El expediente agrupa el RUT consultado con posibles datos asociados, separando hechos confirmados, hipótesis y tareas humanas pendientes. La prioridad operativa es validar manualmente las fuentes autorizadas, capturar evidencia verificable y convertir las observaciones en nodos relacionados.", key_findings: ["El RUT fue normalizado y queda disponible como entidad pivote.", "Existen entidades asociadas de ejemplo para demostrar teléfono, patente y persona.", "La tarea HITL muestra cómo continuar una revisión humana y guardar evidencia estructurada."], gaps: ["No hay confirmación oficial porque la API local no está conectada en esta vista.", "Las relaciones demo deben reemplazarse por evidencia real obtenida desde transformaciones y fuentes autorizadas."], recommended_next_steps: ["Levantar backend con Docker Compose o API local.", "Ejecutar transformaciones de RUT, teléfono y patente.", "Abrir tareas HITL, capturar extractos y guardar entidades observadas."], entity_type_distribution: { Seed: 1, Person: 1, Phone: 1, Plate: 1, HumanTask: 1 }, ai_status: "Narrativa demostrativa local; no reemplaza la verificación de fuentes." },
    entities: demoNodes,
    entity_profiles: demoNodes.map((entity) => ({ entity, analysis: { title: entity.label, summary: `${entity.label} aparece como entidad del expediente. Revisa relaciones, evidencia y tareas pendientes antes de considerarlo confirmado.`, facts: [`Tipo: ${entity.type}`, `Valor: ${entity.value}`], gaps: ["Requiere validación con fuentes autorizadas."], next_steps: ["Ejecutar transformaciones relacionadas y guardar evidencia HITL."], mode: "demo" }, relationships: [], evidence: [], stats: { relationships: demoEdges.filter((edge) => edge.source === entity.id || edge.target === entity.id).length, evidence: entity.type === "Seed" ? 1 : 0, human_tasks: entity.type === "HumanTask" ? 1 : 0, confidence: entity.confidence } })),
    relationships: demoEdges.map((edge) => ({ id: edge.id, type: edge.type, source_id: edge.source, source_label: demoNodes.find((node) => node.id === edge.source)?.label || edge.source, source_type: demoNodes.find((node) => node.id === edge.source)?.type, target_id: edge.target, target_label: demoNodes.find((node) => node.id === edge.target)?.label || edge.target, target_type: demoNodes.find((node) => node.id === edge.target)?.type, properties: edge.properties, confidence: edge.confidence })),
    evidence: [{ id: "ev-demo-1", source_name: "demo", source_url: "", extract: "RUT normalizado en formato chileno y preparado para transformaciones derivadas.", confidence: 0.75, properties: { demo: true }, created_at: new Date().toISOString() }, { id: "ev-demo-2", source_name: "demo", source_url: "", extract: "La relación con teléfono y patente se presenta como hipótesis de demostración hasta capturar evidencia humana.", confidence: 0.52, properties: { demo: true }, created_at: new Date().toISOString() }],
    human_tasks: [demoNodes[4] as HumanTaskItem],
    runs: [{ id: "run-demo-1", transform_id: "cl.rut.normalize", input_type: "rut", input_value: "12.345.678-5", created_at: new Date().toISOString(), output_summary: { entities: 1, human_tasks: 0, relationships: 0 } }, { id: "run-demo-2", transform_id: "cl.rut.open_sources.hitl", input_type: "rut", input_value: "12.345.678-5", created_at: new Date().toISOString(), output_summary: { entities: 1, human_tasks: 1, relationships: 1 } }],
    timeline: [{ at: new Date().toISOString(), kind: "demo", title: "Expediente inicializado", detail: "Vista offline con datos demostrativos para revisar la experiencia de análisis.", confidence: 0.7 }],
    visualizations: { treemap: [{ name: "Seed", size: 1 }, { name: "Person", size: 1 }, { name: "Phone", size: 1 }, { name: "Plate", size: 1 }, { name: "HumanTask", size: 1 }], sankey: { nodes: [{ name: "cl.rut.normalize" }, { name: "cl.rut.open_sources.hitl" }, { name: "Seed" }, { name: "HumanTask" }], links: [{ source: 0, target: 2, value: 1 }, { source: 1, target: 3, value: 1 }] }, semantic_clusters: [{ name: "identidad", count: 2, avg_confidence: 0.72, examples: [] }, { name: "contacto", count: 1, avg_confidence: 0.71, examples: [] }, { name: "vehículo", count: 1, avg_confidence: 0.63, examples: [] }] },
  };
}

function buildMarkdownReport(report: FindingsReport | null) {
  if (!report) return "# Expediente OSINT\n\nSin datos cargados.";
  const lines = [
    `# Expediente OSINT: ${report.investigation.title}`,
    "",
    `**Objetivo:** ${report.investigation.objective || "Sin objetivo declarado."}`,
    "",
    "## Síntesis asistida por IA",
    "",
    report.analysis?.executive_summary || "Sin síntesis disponible.",
    "",
    "## Hallazgos clave",
    "",
    ...(report.analysis?.key_findings || []).map((item) => `- ${item}`),
    "",
    "## Entidades principales",
    "",
    "| Tipo | Etiqueta | Confianza | Evidencias | Relaciones |",
    "|---|---:|---:|---:|---:|",
    ...(report.entity_profiles || []).slice(0, 25).map((profile) => `| ${profile.entity.type} | ${profile.entity.label} | ${formatConfidence(profile.entity.confidence)} | ${profile.stats.evidence} | ${profile.stats.relationships} |`),
    "",
    "## Brechas y próximos pasos",
    "",
    ...(report.analysis?.gaps || []).map((item) => `- ${item}`),
    ...(report.analysis?.recommended_next_steps || []).map((item) => `- ${item}`),
  ];
  return lines.join("\n");
}

function FindingMetric({ label, value, icon: Icon }: { label: string; value: string | number; icon: IconType }) {
  return (
    <div className="border border-[#597060]/40 bg-black/20 p-4">
      <Icon className="mb-3 h-5 w-5 text-[#d49b4a]" />
      <strong className="block font-mono text-2xl text-[#f1ead9]">{value}</strong>
      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#81a684]">{label}</span>
    </div>
  );
}

function MiniGraph({ nodes, edges, onSelectEntity }: { nodes: GraphNode[]; edges: GraphEdge[]; onSelectEntity: (id: string) => void }) {
  const positioned = useMemo(() => graphLayout(nodes.slice(0, 28)), [nodes]);
  const lookup = useMemo(() => Object.fromEntries(positioned.map((node) => [node.id, node])), [positioned]);

  if (!positioned.length) {
    return (
      <div className="grid h-full min-h-[620px] place-items-center p-8 text-center">
        <div className="max-w-lg border border-[#597060]/40 bg-[#0b1110]/86 p-8">
          <Search className="mx-auto mb-4 h-10 w-10 text-[#d49b4a]" />
          <h3 className="mb-3 font-display text-2xl">Agrega una semilla para iniciar el expediente gráfico</h3>
          <p className="text-[#a9b5a6]">RUT, email .cl, teléfono, patente, dominio, nombre o empresa pueden convertirse en nodos iniciales y perfiles legibles.</p>
        </div>
      </div>
    );
  }

  return (
    <svg viewBox="0 0 880 520" className="relative h-full min-h-[620px] w-full">
      <defs>
        <filter id="nodeGlow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="6" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {edges.slice(0, 80).map((edge) => {
        const source = lookup[edge.source];
        const target = lookup[edge.target];
        if (!source || !target) return null;
        const color = edge.type === "REQUIRES_HUMAN" ? "#d49b4a" : edge.type === "CONFIRMED_BY_HUMAN" ? "#81a684" : "#6f8f7d";
        return <line key={edge.id} x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke={color} strokeOpacity="0.55" strokeWidth={edge.type === "REQUIRES_HUMAN" ? 2.4 : 1.4} strokeDasharray={edge.type === "REQUIRES_HUMAN" ? "7 5" : undefined} />;
      })}
      {positioned.map((node) => {
        const color = nodeColor(node.type);
        return (
          <g key={node.id} role="button" tabIndex={0} onClick={() => onSelectEntity(node.id)} className="cursor-pointer outline-none">
            <circle cx={node.x} cy={node.y} r={node.type === "Seed" ? 34 : 27} fill="#0d1211" stroke={color} strokeWidth="2" filter="url(#nodeGlow)" />
            <text x={node.x} y={node.y - 5} textAnchor="middle" fill={color} fontFamily="IBM Plex Mono" fontSize="10" fontWeight="700">{node.type.slice(0, 10)}</text>
            <text x={node.x} y={node.y + 10} textAnchor="middle" fill="#f1ead9" fontFamily="IBM Plex Mono" fontSize="9">{node.label.slice(0, 20)}</text>
          </g>
        );
      })}
    </svg>
  );
}

function EntityProfileCard({ profile, selected, onSelect }: { profile: EntityProfile; selected: boolean; onSelect: () => void }) {
  return (
    <button onClick={onSelect} className={`w-full border p-4 text-left transition ${selected ? "border-[#d49b4a]/80 bg-[#d49b4a]/12" : "border-[#597060]/35 bg-black/20 hover:border-[#81a684]/60"}`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em]" style={{ borderColor: nodeColor(profile.entity.type), color: nodeColor(profile.entity.type) }}>{profile.entity.type}</span>
        <span className={`border px-2 py-1 font-mono text-[10px] ${confidenceTone(profile.entity.confidence)}`}>confianza {formatConfidence(profile.entity.confidence)}</span>
      </div>
      <h4 className="font-display text-xl text-[#f1ead9]">{profile.entity.label}</h4>
      <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-[#a9b5a6]">{profile.analysis.summary}</p>
      <div className="mt-4 grid grid-cols-3 gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-[#81a684]">
        <span className="border border-[#597060]/30 bg-black/25 p-2">Ev: {profile.stats.evidence}</span>
        <span className="border border-[#597060]/30 bg-black/25 p-2">Rel: {profile.stats.relationships}</span>
        <span className="border border-[#597060]/30 bg-black/25 p-2">HITL: {profile.stats.human_tasks}</span>
      </div>
    </button>
  );
}

function SankeyPreview({ report }: { report: FindingsReport }) {
  const nodes = report.visualizations?.sankey.nodes || [];
  const links = report.visualizations?.sankey.links || [];
  if (!nodes.length || !links.length) return <p className="border border-[#597060]/30 bg-black/20 p-4 text-sm text-[#a9b5a6]">No hay suficientes ejecuciones para dibujar un Sankey.</p>;
  const left = nodes.slice(0, Math.ceil(nodes.length / 2));
  const right = nodes.slice(Math.ceil(nodes.length / 2));
  return (
    <div className="border border-[#597060]/35 bg-black/20 p-4">
      <svg viewBox="0 0 760 280" className="h-72 w-full">
        {links.slice(0, 20).map((link, index) => {
          const y1 = 40 + ((link.source % Math.max(left.length, 1)) * 180) / Math.max(left.length - 1, 1);
          const y2 = 40 + ((link.target % Math.max(right.length, 1)) * 180) / Math.max(right.length - 1, 1);
          return <path key={`${link.source}-${link.target}-${index}`} d={`M 180 ${y1} C 300 ${y1}, 440 ${y2}, 580 ${y2}`} fill="none" stroke={index % 2 ? "#81a684" : "#d49b4a"} strokeOpacity="0.45" strokeWidth={Math.max(2, link.value * 4)} />;
        })}
        {left.map((node, index) => <g key={node.name}><rect x="20" y={26 + index * 42} width="210" height="28" fill="#101817" stroke="#597060" /><text x="32" y={45 + index * 42} fill="#f1ead9" fontSize="10" fontFamily="IBM Plex Mono">{node.name.slice(0, 30)}</text></g>)}
        {right.map((node, index) => <g key={node.name}><rect x="530" y={26 + index * 42} width="210" height="28" fill="#101817" stroke="#597060" /><text x="542" y={45 + index * 42} fill="#f1ead9" fontSize="10" fontFamily="IBM Plex Mono">{node.name.slice(0, 30)}</text></g>)}
      </svg>
    </div>
  );
}

function HitlWorkspace({ report, selectedTaskId, setSelectedTaskId, draft, setDraft, onSubmit }: { report: FindingsReport; selectedTaskId: string | null; setSelectedTaskId: (id: string) => void; draft: HitlDraft; setDraft: (draft: HitlDraft) => void; onSubmit: (task: HumanTaskItem) => void }) {
  const tasks = report.human_tasks || [];
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) || tasks[0];
  const searchUrl = selectedTask?.properties.search_url || "about:blank";

  if (!selectedTask) {
    return <p className="border border-[#597060]/35 bg-black/20 p-4 text-sm text-[#a9b5a6]">No hay tareas human-in-the-loop. Ejecuta transformaciones que requieran revisión manual para abrir el workspace operativo.</p>;
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <div className="space-y-3">
        {tasks.map((task) => (
          <button key={task.id} onClick={() => setSelectedTaskId(task.id)} className={`w-full border p-4 text-left transition ${selectedTask.id === task.id ? "border-[#d49b4a]/80 bg-[#d49b4a]/12" : "border-[#597060]/35 bg-black/20 hover:bg-[#597060]/12"}`}>
            <div className="mb-2 flex items-center justify-between gap-2"><span className="font-display text-lg text-[#f1ead9]">{task.label}</span><span className="font-mono text-[10px] text-[#e6c27a]">{task.status || task.properties.status || "pendiente"}</span></div>
            <p className="font-mono text-xs text-[#c7b68b]">{task.value}</p>
            <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-[#a9b5a6]">{String(task.properties.purpose || task.properties.instructions || "Revisión manual autorizada")}</p>
          </button>
        ))}
      </div>
      <div className="grid gap-5 2xl:grid-cols-[1fr_420px]">
        <section className="overflow-hidden border border-[#597060]/35 bg-black/20">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#597060]/35 p-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#81a684]">Navegador integrado HITL</p>
              <h4 className="font-display text-xl text-[#f1ead9]">{selectedTask.properties.source || selectedTask.label}</h4>
            </div>
            <a href={String(searchUrl)} target="_blank" rel="noreferrer" className="inline-flex items-center border border-[#d49b4a]/55 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[#e6c27a] hover:bg-[#d49b4a]/12">
              <ExternalLink className="mr-2 h-4 w-4" /> Abrir externo
            </a>
          </div>
          <div className="border-b border-[#597060]/25 bg-[#101817] px-4 py-3 font-mono text-[11px] text-[#c7b68b]">{String(searchUrl)}</div>
          <iframe title="HITL browser" src={String(searchUrl)} sandbox="allow-forms allow-popups allow-scripts allow-same-origin" className="h-[560px] w-full bg-[#f7f2e6]" />
          <p className="border-t border-[#597060]/25 p-3 text-xs leading-relaxed text-[#a9b5a6]">Algunas fuentes bloquean iframes por política de seguridad. En ese caso usa “Abrir externo”, revisa la fuente autorizada y vuelve a esta ficha para guardar extracto, URL, confianza y entidades observadas.</p>
        </section>
        <section className="border border-[#d49b4a]/35 bg-[#d49b4a]/8 p-5">
          <div className="mb-4 flex items-center gap-3"><LockKeyhole className="h-5 w-5 text-[#d49b4a]" /><h4 className="font-display text-xl">Guardar respuesta humana</h4></div>
          <label className="mb-2 block text-sm text-[#d2d0c7]">Fuente consultada</label>
          <input value={draft.source_name} onChange={(event) => setDraft({ ...draft, source_name: event.target.value })} className="mb-3 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-sm outline-none focus:border-[#d49b4a]" />
          <label className="mb-2 block text-sm text-[#d2d0c7]">URL / referencia</label>
          <input value={draft.source_url} onChange={(event) => setDraft({ ...draft, source_url: event.target.value })} className="mb-3 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-sm outline-none focus:border-[#d49b4a]" />
          <label className="mb-2 block text-sm text-[#d2d0c7]">Extracto verificable</label>
          <textarea value={draft.extract} onChange={(event) => setDraft({ ...draft, extract: event.target.value })} rows={5} className="mb-3 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 text-sm leading-relaxed outline-none focus:border-[#d49b4a]" />
          <div className="mb-3 grid grid-cols-2 gap-3">
            <div><label className="mb-2 block text-sm text-[#d2d0c7]">Estado</label><select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value as HitlDraft["status"] })} className="w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-xs outline-none focus:border-[#d49b4a]"><option value="confirmed">Confirmado</option><option value="no_result">Sin resultado</option><option value="needs_follow_up">Requiere seguimiento</option><option value="discarded">Descartado</option></select></div>
            <div><label className="mb-2 block text-sm text-[#d2d0c7]">Confianza</label><input type="number" min="0" max="1" step="0.05" value={draft.confidence} onChange={(event) => setDraft({ ...draft, confidence: Number(event.target.value) })} className="w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-sm outline-none focus:border-[#d49b4a]" /></div>
          </div>
          <label className="mb-2 block text-sm text-[#d2d0c7]">Entidades observadas, una por línea: tipo | etiqueta | valor</label>
          <textarea value={draft.observed} onChange={(event) => setDraft({ ...draft, observed: event.target.value })} rows={4} placeholder="Person | Juan Pérez | Juan Pérez\nPhone | +56987654321 | +56987654321" className="mb-3 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-xs outline-none focus:border-[#d49b4a]" />
          <label className="mb-2 block text-sm text-[#d2d0c7]">Notas del operador</label>
          <textarea value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} rows={3} className="mb-4 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 text-sm outline-none focus:border-[#d49b4a]" />
          <Button onClick={() => onSubmit(selectedTask)} className="w-full rounded-none bg-[#d49b4a] text-[#16110b] hover:bg-[#e6c27a]"><Database className="mr-2 h-4 w-4" />Guardar en banco del objetivo</Button>
        </section>
      </div>
    </div>
  );
}

function FindingsPanel({ report, activeTab, setActiveTab, selectedEntityId, setSelectedEntityId, selectedTaskId, setSelectedTaskId, hitlDraft, setHitlDraft, onCompleteTask, onRefresh, onCopyReport }: { report: FindingsReport | null; activeTab: FindingTab; setActiveTab: (tab: FindingTab) => void; selectedEntityId: string | null; setSelectedEntityId: (id: string) => void; selectedTaskId: string | null; setSelectedTaskId: (id: string) => void; hitlDraft: HitlDraft; setHitlDraft: (draft: HitlDraft) => void; onCompleteTask: (task: HumanTaskItem) => void; onRefresh: () => void; onCopyReport: () => void }) {
  const profiles = report?.entity_profiles || [];
  const selectedProfile = profiles.find((profile) => profile.entity.id === selectedEntityId) || profiles[0];

  if (!report) {
    return (
      <section className="mx-5 mb-5 border border-[#597060]/40 bg-[#101817]/85 p-8 text-center">
        <ClipboardList className="mx-auto mb-4 h-10 w-10 text-[#d49b4a]" />
        <h3 className="font-display text-2xl">Aún no hay expediente detallado cargado</h3>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-[#a9b5a6]">Agrega una semilla o ejecuta una transformación. El informe consolidará fichas por entidad, narrativa asistida por IA, relaciones, evidencias, tareas HITL accionables y visualizaciones.</p>
      </section>
    );
  }

  return (
    <section className="mx-5 mb-5 border border-[#597060]/40 bg-[#101817]/90 shadow-[0_28px_90px_rgba(0,0,0,.34)]">
      <div className="border-b border-[#597060]/35 p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.34em] text-[#81a684]">Expediente accionable · hallazgos legibles · banco de datos del objetivo</p>
            <h3 className="font-display text-3xl font-semibold text-[#f1ead9]">{report.investigation.title}</h3>
            <p className="mt-3 max-w-4xl text-sm leading-relaxed text-[#a9b5a6]">{report.investigation.objective || report.analysis?.executive_summary}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={onCopyReport} className="rounded-none border border-[#d49b4a]/60 bg-[#d49b4a]/10 text-[#e6c27a] hover:bg-[#d49b4a]/18"><Copy className="mr-2 h-4 w-4" />Copiar informe</Button>
            <Button onClick={onRefresh} className="rounded-none border border-[#597060]/60 bg-black/20 text-[#f1ead9] hover:bg-[#597060]/25"><RefreshCw className="mr-2 h-4 w-4" />Refrescar</Button>
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <FindingMetric icon={Target} label="Entidades" value={report.summary.entities} />
          <FindingMetric icon={GitBranch} label="Relaciones" value={report.summary.relationships} />
          <FindingMetric icon={FileText} label="Evidencias" value={report.summary.evidence} />
          <FindingMetric icon={AlertTriangle} label="HITL pendientes" value={report.summary.pending_human_tasks ?? report.summary.human_tasks} />
          <FindingMetric icon={Activity} label="Transforms" value={report.summary.transform_runs} />
          <FindingMetric icon={ShieldCheck} label="Confianza media" value={formatConfidence(report.summary.average_confidence)} />
        </div>
      </div>

      <div className="flex flex-wrap border-b border-[#597060]/35 bg-black/15">
        {findingTabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`border-r border-[#597060]/30 px-4 py-3 font-mono text-[11px] uppercase tracking-[0.18em] transition ${activeTab === tab.id ? "bg-[#d49b4a]/16 text-[#e6c27a]" : "text-[#a9b5a6] hover:bg-[#597060]/12 hover:text-[#f1ead9]"}`}>{tab.label}</button>
        ))}
      </div>

      <div className="p-6">
        {activeTab === "dossier" && (
          <div className="grid gap-5 xl:grid-cols-[1.1fr_.9fr]">
            <article className="border border-[#597060]/35 bg-black/20 p-6">
              <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.22em] text-[#81a684]">Narrativa asistida por IA</p>
              <h4 className="font-display text-2xl text-[#f1ead9]">Descripción del objetivo y lectura de hallazgos</h4>
              <p className="mt-4 text-base leading-relaxed text-[#d2d0c7]">{report.analysis?.executive_summary}</p>
              <p className="mt-3 border border-[#597060]/30 bg-[#101817]/70 p-3 font-mono text-[11px] text-[#c7b68b]">{report.analysis?.ai_status || "Narrativa generada por razonamiento local asistido."}</p>
            </article>
            <article className="border border-[#597060]/35 bg-black/20 p-6">
              <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.22em] text-[#81a684]">Hallazgos clave</p>
              <div className="space-y-3">{(report.analysis?.key_findings || []).map((item) => <p key={item} className="border-l border-[#d49b4a]/55 bg-[#d49b4a]/8 p-3 text-sm leading-relaxed text-[#f1ead9]">{item}</p>)}</div>
            </article>
            <article className="border border-[#597060]/35 bg-black/20 p-6">
              <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.22em] text-[#81a684]">Brechas</p>
              <div className="space-y-3">{(report.analysis?.gaps || []).map((item) => <p key={item} className="text-sm leading-relaxed text-[#a9b5a6]">{item}</p>)}</div>
            </article>
            <article className="border border-[#597060]/35 bg-black/20 p-6">
              <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.22em] text-[#81a684]">Próximas acciones</p>
              <div className="space-y-3">{(report.analysis?.recommended_next_steps || []).map((item) => <p key={item} className="text-sm leading-relaxed text-[#d2d0c7]">{item}</p>)}</div>
            </article>
          </div>
        )}

        {activeTab === "entities" && (
          <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
            <div className="max-h-[760px] space-y-3 overflow-auto pr-2">{profiles.map((profile) => <EntityProfileCard key={profile.entity.id} profile={profile} selected={selectedProfile?.entity.id === profile.entity.id} onSelect={() => setSelectedEntityId(profile.entity.id)} />)}</div>
            {selectedProfile ? (
              <article className="border border-[#597060]/35 bg-black/20 p-6">
                <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                  <div><p className="font-mono text-[10px] uppercase tracking-[0.22em] text-[#81a684]">Ficha individual</p><h4 className="mt-2 font-display text-3xl text-[#f1ead9]">{selectedProfile.entity.label}</h4></div>
                  <span className={`border px-3 py-2 font-mono text-[11px] ${confidenceTone(selectedProfile.entity.confidence)}`}>{formatConfidence(selectedProfile.entity.confidence)}</span>
                </div>
                <p className="text-base leading-relaxed text-[#d2d0c7]">{selectedProfile.analysis.summary}</p>
                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                  <div><p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-[#e6c27a]">Datos asociados</p><p className="border border-[#597060]/30 bg-[#101817]/80 p-4 text-sm leading-relaxed text-[#a9b5a6]">{formatProperties(selectedProfile.entity.properties)}</p></div>
                  <div><p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-[#e6c27a]">Brechas de la ficha</p><div className="space-y-2">{selectedProfile.analysis.gaps.map((gap) => <p key={gap} className="border border-[#597060]/25 bg-[#101817]/80 p-3 text-sm text-[#a9b5a6]">{gap}</p>)}</div></div>
                </div>
                <div className="mt-6 grid gap-4 xl:grid-cols-2">
                  <div><p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-[#e6c27a]">Relaciones directas</p><div className="max-h-72 space-y-2 overflow-auto">{selectedProfile.relationships.map((rel) => <p key={rel.id} className="border-l border-[#d49b4a]/55 bg-black/20 p-3 text-sm text-[#d2d0c7]">{rel.source_label} <span className="font-mono text-[#e6c27a]">{rel.type}</span> {rel.target_label}</p>)}</div></div>
                  <div><p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-[#e6c27a]">Evidencias asociadas</p><div className="max-h-72 space-y-2 overflow-auto">{selectedProfile.evidence.map((ev) => <p key={ev.id} className="border-l border-[#81a684]/55 bg-black/20 p-3 text-sm text-[#d2d0c7]">{ev.extract}</p>)}</div></div>
                </div>
              </article>
            ) : <p className="text-sm text-[#a9b5a6]">Sin entidades para perfilar.</p>}
          </div>
        )}

        {activeTab === "tasks" && <HitlWorkspace report={report} selectedTaskId={selectedTaskId} setSelectedTaskId={setSelectedTaskId} draft={hitlDraft} setDraft={setHitlDraft} onSubmit={onCompleteTask} />}

        {activeTab === "visual" && (
          <div className="grid gap-5 xl:grid-cols-2">
            <article className="border border-[#597060]/35 bg-black/20 p-5"><div className="mb-4 flex items-center gap-3"><Layers3 className="h-5 w-5 text-[#81a684]" /><h4 className="font-display text-xl">Treemap de entidades del objetivo</h4></div><div className="flex h-80 flex-wrap content-stretch gap-2 overflow-hidden">{(report.visualizations?.treemap || []).map((item, index) => <div key={item.name} className="grid place-items-center border border-[#597060]/35 bg-[#101817] p-3 text-center" style={{ flexBasis: `${Math.max(18, Math.min(48, item.size * 12))}%`, flexGrow: item.size, borderColor: nodeColor(item.name) }}><strong className="font-display text-2xl text-[#f1ead9]">{item.size}</strong><span className="font-mono text-[10px] uppercase tracking-[0.16em]" style={{ color: nodeColor(item.name) }}>{item.name}</span></div>)}</div></article>
            <article className="border border-[#597060]/35 bg-black/20 p-5"><div className="mb-4 flex items-center gap-3"><Split className="h-5 w-5 text-[#d49b4a]" /><h4 className="font-display text-xl">Sankey de transforms → hallazgos</h4></div><SankeyPreview report={report} /></article>
            <article className="xl:col-span-2 border border-[#597060]/35 bg-black/20 p-5"><div className="mb-4 flex items-center gap-3"><Route className="h-5 w-5 text-[#e6c27a]" /><h4 className="font-display text-xl">Relaciones semánticas</h4></div><div className="grid gap-3 md:grid-cols-3">{(report.visualizations?.semantic_clusters || []).map((cluster) => <div key={cluster.name} className="border border-[#597060]/30 bg-[#101817]/70 p-4"><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#81a684]">{cluster.name}</p><strong className="mt-2 block font-display text-3xl text-[#f1ead9]">{cluster.count}</strong><p className="mt-2 text-sm text-[#a9b5a6]">Confianza media {formatConfidence(cluster.avg_confidence)}</p></div>)}</div></article>
          </div>
        )}

        {activeTab === "relationships" && <RelationshipTable relationships={report.relationships} />}
        {activeTab === "evidence" && <EvidenceList report={report} />}
        {activeTab === "runs" && <RunsTable report={report} />}
        {activeTab === "timeline" && <TimelineList report={report} />}
      </div>
    </section>
  );
}

function RelationshipTable({ relationships }: { relationships: FindingRelationship[] }) {
  return <div className="space-y-3">{relationships.map((relationship) => <article key={relationship.id} className="grid gap-3 border border-[#597060]/35 bg-black/20 p-4 lg:grid-cols-[1fr_auto_1fr] lg:items-center"><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#81a684]">Origen</p><h4 className="mt-1 text-[#f1ead9]">{relationship.source_label}</h4><p className="font-mono text-[10px] text-[#a9b5a6]">{relationship.source_type}</p></div><div className="border border-[#d49b4a]/45 px-3 py-2 text-center font-mono text-[10px] uppercase tracking-[0.18em] text-[#e6c27a]">{relationship.type}<br />{formatConfidence(relationship.confidence)}</div><div><p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#81a684]">Destino</p><h4 className="mt-1 text-[#f1ead9]">{relationship.target_label}</h4><p className="font-mono text-[10px] text-[#a9b5a6]">{relationship.target_type}</p></div></article>)}</div>;
}

function EvidenceList({ report }: { report: FindingsReport }) {
  return <div className="space-y-3">{report.evidence.map((evidence) => <article key={evidence.id} className="border border-[#597060]/35 bg-black/20 p-4"><div className="mb-3 flex flex-wrap items-center justify-between gap-2"><span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#e6c27a]">{evidence.source_name}</span><span className={`border px-2 py-1 font-mono text-[10px] ${confidenceTone(evidence.confidence)}`}>{formatConfidence(evidence.confidence)}</span></div><p className="text-sm leading-relaxed text-[#d2d0c7]">{evidence.extract}</p>{evidence.source_url && <a href={evidence.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center font-mono text-[11px] text-[#81a684] hover:text-[#e6c27a]"><ExternalLink className="mr-2 h-3 w-3" />{evidence.source_url}</a>}<p className="mt-3 font-mono text-[11px] text-[#81a684]">{new Date(evidence.created_at).toLocaleString("es-CL")}</p><p className="mt-2 text-xs text-[#a9b5a6]">{formatProperties(evidence.properties)}</p></article>)}</div>;
}

function RunsTable({ report }: { report: FindingsReport }) {
  return <div className="overflow-auto border border-[#597060]/30"><table className="w-full min-w-[760px] border-collapse text-left text-sm"><thead className="bg-black/30 font-mono text-[10px] uppercase tracking-[0.18em] text-[#81a684]"><tr><th className="p-3">Transform</th><th className="p-3">Entrada</th><th className="p-3">Entidades</th><th className="p-3">HITL</th><th className="p-3">Fecha</th></tr></thead><tbody>{report.runs.map((run) => <tr key={run.id} className="border-t border-[#597060]/25 text-[#d2d0c7]"><td className="p-3 font-mono text-[#e6c27a]">{run.transform_id}</td><td className="p-3">{run.input_type}={run.input_value}</td><td className="p-3">{run.output_summary.entities}</td><td className="p-3">{run.output_summary.human_tasks}</td><td className="p-3">{new Date(run.created_at).toLocaleString("es-CL")}</td></tr>)}</tbody></table></div>;
}

function TimelineList({ report }: { report: FindingsReport }) {
  return <div className="space-y-3">{report.timeline.map((item, index) => <article key={`${item.at}-${index}`} className="border-l border-[#d49b4a]/50 bg-black/20 p-4"><div className="mb-2 flex flex-wrap justify-between gap-2"><span className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#e6c27a]">{item.kind} · {item.title}</span><span className="font-mono text-[11px] text-[#81a684]">{new Date(item.at).toLocaleString("es-CL")}</span></div><p className="text-sm leading-relaxed text-[#d2d0c7]">{item.detail}</p></article>)}</div>;
}

export default function Home() {
  const [health, setHealth] = useState<string>("conectando");
  const [transforms, setTransforms] = useState<Transform[]>([]);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [findings, setFindings] = useState<FindingsReport | null>(null);
  const [activeFindingTab, setActiveFindingTab] = useState<FindingTab>("dossier");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [inputType, setInputType] = useState("rut");
  const [value, setValue] = useState("12.345.678-5");
  const [selectedTransform, setSelectedTransform] = useState("cl.rut.normalize");
  const [log, setLog] = useState<string[]>(["Estación OSINT inicializada. El producto principal ahora es el expediente; la bitácora queda como soporte técnico."]);
  const [aiResult, setAiResult] = useState("");
  const [hitlDraft, setHitlDraft] = useState<HitlDraft>({ source_name: "Fuente revisada por operador", source_url: "", extract: "", confidence: 0.72, status: "confirmed", observed: "", notes: "" });

  const investigationId = "demo";

  const refreshFindings = useCallback(async () => {
    try {
      const report = await api.findings(investigationId);
      setFindings(report);
      if (!selectedEntityId && report.entity_profiles?.[0]) setSelectedEntityId(report.entity_profiles[0].entity.id);
      if (!selectedTaskId && report.human_tasks?.[0]) setSelectedTaskId(report.human_tasks[0].id);
    } catch {
      const demo = createDemoReport();
      setFindings(demo);
      if (!selectedEntityId && demo.entity_profiles?.[0]) setSelectedEntityId(demo.entity_profiles[0].entity.id);
      if (!selectedTaskId && demo.human_tasks?.[0]) setSelectedTaskId(demo.human_tasks[0].id);
    }
  }, [selectedEntityId, selectedTaskId]);

  const refreshGraph = useCallback(async () => {
    try {
      const graph = await api.graph(investigationId);
      setGraphNodes(graph.nodes);
      setGraphEdges(graph.edges);
    } catch {
      setGraphNodes(demoNodes);
      setGraphEdges(demoEdges);
    }
  }, []);

  const refreshWorkspace = useCallback(async () => {
    await Promise.all([refreshGraph(), refreshFindings().catch(() => undefined)]);
  }, [refreshGraph, refreshFindings]);

  useEffect(() => {
    api.health().then((data) => setHealth(`${data.status} · ${data.ai_provider}`)).catch(() => setHealth("api offline · demo local"));
    api.transforms().then((items) => { setTransforms(items); setSelectedTransform(items[0]?.id || "cl.rut.normalize"); }).catch(() => { setTransforms([{ id: "cl.rut.normalize", name: "Normalizar RUT", description: "Transformación demo disponible cuando la API no está levantada.", input_types: ["rut"], output_types: ["Seed"], execution_mode: "automatic", risk_level: "low", requires_human: false, source_policy: "demo" }, { id: "cl.rut.open_sources.hitl", name: "Revisión humana de fuentes", description: "Abre una compuerta HITL para capturar evidencia manual.", input_types: ["rut"], output_types: ["HumanTask"], execution_mode: "human_in_the_loop", risk_level: "medium", requires_human: true, source_policy: "human" }]); setLog((current) => ["API no disponible: usando catálogo demo local para previsualizar expediente.", ...current]); });
    refreshWorkspace().catch(() => undefined);
  }, [refreshWorkspace]);

  const availableTransforms = useMemo(() => transforms.filter((transform) => transform.input_types.includes(inputType) || transform.id.startsWith("cl.dork") || transform.id.includes("human")), [transforms, inputType]);
  const groupedTransforms = useMemo(() => availableTransforms.reduce<Record<string, number>>((acc, transform) => { const category = transform.execution_mode === "human_in_the_loop" ? "hitl" : transform.risk_level; acc[category] = (acc[category] || 0) + 1; return acc; }, {}), [availableTransforms]);

  async function addSeed() {
    await api.addSeed({ investigation_id: investigationId, input_type: inputType, value });
    setLog((current) => [`Semilla agregada: ${inputType}=${value}`, ...current]);
    await refreshWorkspace();
  }

  async function runTransform() {
    try {
      const result = await api.runTransform({ investigation_id: investigationId, transform_id: selectedTransform, input_type: inputType, value });
      setLog((current) => [`Transform ejecutado: ${selectedTransform} · entidades: ${result.created_entities.length}`, ...current]);
      await refreshWorkspace();
    } catch (error) {
      setLog((current) => [`Error transform: ${(error as Error).message}`, ...current]);
    }
  }

  async function runAiSummary() {
    try {
      const report = await api.findings(investigationId);
      const result = await api.aiRun({ prompt_id: "semantic_summary", variables: { evidence: buildMarkdownReport(report) }, provider: "mock" });
      setAiResult(result.content);
      setLog((current) => ["Síntesis IA solicitada con proveedor mock/configurable.", ...current]);
    } catch (error) {
      setLog((current) => [`Error IA: ${(error as Error).message}`, ...current]);
    }
  }

  async function completeHumanTask(task: HumanTaskItem) {
    try {
      await api.completeHumanTask(task.id, { investigation_id: investigationId, task_entity_id: task.id, source_name: hitlDraft.source_name, source_url: hitlDraft.source_url || task.properties.search_url || "", extract: hitlDraft.extract, confidence: hitlDraft.confidence, status: hitlDraft.status, observed_entities: parseObservedEntities(hitlDraft.observed), notes: hitlDraft.notes });
      setHitlDraft({ source_name: "Fuente revisada por operador", source_url: "", extract: "", confidence: 0.72, status: "confirmed", observed: "", notes: "" });
      setLog((current) => [`Tarea HITL guardada en banco: ${task.label}`, ...current]);
      await refreshWorkspace();
    } catch (error) {
      setLog((current) => [`Error guardando HITL: ${(error as Error).message}`, ...current]);
    }
  }

  async function copyReport() {
    const markdown = buildMarkdownReport(findings);
    await navigator.clipboard?.writeText(markdown);
    setLog((current) => ["Informe Markdown copiado al portapapeles.", ...current]);
  }

  return (
    <main className="min-h-screen bg-[#0a0f0e] text-[#f1ead9] selection:bg-[#d49b4a]/30" style={{ backgroundImage: `linear-gradient(90deg, rgba(10,15,14,.96), rgba(10,15,14,.82)), url(${HERO_URL})`, backgroundSize: "cover", backgroundAttachment: "fixed" }}>
      <section className="grid min-h-screen grid-cols-1 xl:grid-cols-[380px_1fr]">
        <aside className="border-r border-[#597060]/35 bg-[#0b1110]/90 p-6 backdrop-blur-xl">
          <div className="mb-8 flex items-center gap-3"><div className="grid h-12 w-12 place-items-center border border-[#d49b4a] bg-[#d49b4a]/10 shadow-[0_0_34px_rgba(212,155,74,.22)]"><Network className="h-6 w-6 text-[#d49b4a]" /></div><div><p className="font-mono text-[10px] uppercase tracking-[0.34em] text-[#81a684]">OSINT Chile</p><h1 className="font-display text-2xl font-semibold tracking-tight">Graph Workbench</h1></div></div>
          <div className="mb-6 grid grid-cols-3 gap-2 text-xs"><div className="border border-[#597060]/40 bg-black/20 p-3"><Database className="mb-2 h-4 w-4 text-[#81a684]" />PostgreSQL</div><div className="border border-[#597060]/40 bg-black/20 p-3"><GitBranch className="mb-2 h-4 w-4 text-[#d49b4a]" />Neo4j</div><div className="border border-[#597060]/40 bg-black/20 p-3"><BrainCircuit className="mb-2 h-4 w-4 text-[#c7b68b]" />AI</div></div>
          <div className="mb-6 border border-[#597060]/40 bg-[#101817]/80 p-4 shadow-[0_18px_60px_rgba(0,0,0,.25)]"><div className="mb-4 flex items-center justify-between"><span className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#81a684]">Semilla</span><span className="border border-[#597060]/40 px-2 py-1 font-mono text-[10px] text-[#c7b68b]">API {health}</span></div><label className="mb-2 block text-sm text-[#d2d0c7]">Tipo de dato inicial</label><select value={inputType} onChange={(event) => setInputType(event.target.value)} className="mb-3 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-sm outline-none focus:border-[#d49b4a]">{inputTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select><label className="mb-2 block text-sm text-[#d2d0c7]">Valor</label><input value={value} onChange={(event) => setValue(event.target.value)} className="mb-4 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-sm outline-none focus:border-[#d49b4a]" /><div className="grid grid-cols-2 gap-3"><Button onClick={addSeed} className="rounded-none bg-[#597060] text-[#f1ead9] hover:bg-[#6f8f7d]"><Fingerprint className="mr-2 h-4 w-4" />Agregar</Button><Button onClick={runTransform} className="rounded-none bg-[#d49b4a] text-[#16110b] hover:bg-[#e6c27a]"><Play className="mr-2 h-4 w-4" />Ejecutar</Button></div></div>
          <div className="mb-6 border border-[#597060]/40 bg-[#101817]/80 p-4"><label className="mb-2 block text-sm text-[#d2d0c7]">Transform</label><select value={selectedTransform} onChange={(event) => setSelectedTransform(event.target.value)} className="w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-xs outline-none focus:border-[#d49b4a]">{availableTransforms.map((transform) => <option key={transform.id} value={transform.id}>{transform.id}</option>)}</select><div className="mt-4 grid grid-cols-2 gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[#81a684]">{Object.entries(groupedTransforms).slice(0, 6).map(([category, count]) => <span key={category} className="border border-[#597060]/30 bg-black/20 px-2 py-2">{category}: {count}</span>)}</div><div className="mt-4 max-h-72 space-y-2 overflow-auto pr-1">{availableTransforms.slice(0, 12).map((transform) => <button key={transform.id} onClick={() => setSelectedTransform(transform.id)} className={`w-full border p-3 text-left transition ${selectedTransform === transform.id ? "border-[#d49b4a]/70 bg-[#d49b4a]/10" : "border-[#597060]/30 bg-black/20 hover:bg-[#597060]/12"}`}><div className="flex items-center justify-between gap-2"><p className="font-mono text-[11px] text-[#e6c27a]">{transform.name}</p>{transform.requires_human ? <LockKeyhole className="h-4 w-4 text-[#d49b4a]" /> : <ShieldCheck className="h-4 w-4 text-[#81a684]" />}</div><p className="mt-1 text-xs leading-relaxed text-[#a9b5a6]">{transform.description}</p></button>)}</div></div>
          <button onClick={runAiSummary} className="group w-full border border-[#d49b4a]/60 bg-[#d49b4a]/10 p-4 text-left transition hover:bg-[#d49b4a]/18"><div className="flex items-center gap-3"><BrainCircuit className="h-5 w-5 text-[#d49b4a]" /><div><p className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#d49b4a]">IA configurable</p><p className="text-sm text-[#f1ead9]">Sintetizar expediente con prompt editable</p></div></div></button>
        </aside>
        <section className="flex min-h-screen flex-col">
          <header className="border-b border-[#597060]/35 bg-[#0b1110]/70 px-8 py-6 backdrop-blur-xl"><div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end"><div><p className="mb-3 font-mono text-[11px] uppercase tracking-[0.34em] text-[#81a684]">Cartografía forense · fichas por entidad · HITL accionable</p><h2 className="max-w-5xl font-display text-4xl font-semibold leading-tight text-[#f1ead9] md:text-6xl">De una semilla chilena a un expediente explicable, visual y continuable.</h2></div><div className="grid grid-cols-3 gap-3 text-center font-mono text-xs"><div className="border border-[#597060]/40 bg-black/25 p-3"><strong className="block text-xl text-[#e6c27a]">{graphNodes.length}</strong>Nodos</div><div className="border border-[#597060]/40 bg-black/25 p-3"><strong className="block text-xl text-[#81a684]">{graphEdges.length}</strong>Relaciones</div><div className="border border-[#597060]/40 bg-black/25 p-3"><strong className="block text-xl text-[#d49b4a]">{findings?.summary.pending_human_tasks ?? 0}</strong>HITL</div></div></div></header>
          <div className="grid flex-1 grid-cols-1 gap-5 p-5 2xl:grid-cols-[1fr_360px]"><div className="relative min-h-[620px] overflow-hidden border border-[#597060]/40 bg-[#0b1110]/82 shadow-[0_28px_90px_rgba(0,0,0,.36)]"><div className="absolute inset-0 opacity-20" style={{ backgroundImage: `url(${GRAPH_PANEL_URL})`, backgroundSize: "cover", backgroundPosition: "center" }} /><div className="absolute inset-0 bg-[linear-gradient(rgba(129,166,132,.06)_1px,transparent_1px),linear-gradient(90deg,rgba(129,166,132,.06)_1px,transparent_1px)] bg-[size:42px_42px]" /><MiniGraph nodes={graphNodes} edges={graphEdges} onSelectEntity={(id) => { setSelectedEntityId(id); setActiveFindingTab("entities"); }} /></div><aside className="space-y-5"><div className="border border-[#597060]/40 bg-[#101817]/85 p-5"><div className="mb-4 flex items-center gap-3"><AlertTriangle className="h-5 w-5 text-[#d49b4a]" /><h3 className="font-display text-xl">Human-in-the-loop</h3></div><img src={HUMAN_LOOP_URL} alt="Representación abstracta de tareas human-in-the-loop" className="mb-4 h-44 w-full object-cover opacity-80" /><p className="text-sm leading-relaxed text-[#a9b5a6]">Las tareas ya no quedan sólo reportadas: se abren en el workspace, se documenta la revisión humana y se insertan evidencia y entidades al banco del objetivo.</p></div><div className="border border-[#597060]/40 bg-[#101817]/85 p-5"><div className="mb-4 flex items-center gap-3"><Layers3 className="h-5 w-5 text-[#81a684]" /><h3 className="font-display text-xl">Resumen de expediente</h3></div><div className="grid grid-cols-2 gap-2 font-mono text-xs"><div className="border border-[#597060]/30 bg-black/20 p-3"><strong className="block text-lg text-[#e6c27a]">{findings?.summary.evidence ?? 0}</strong>Evidencias</div><div className="border border-[#597060]/30 bg-black/20 p-3"><strong className="block text-lg text-[#d49b4a]">{findings?.summary.pending_human_tasks ?? 0}</strong>HITL pendientes</div></div></div><div className="border border-[#597060]/40 bg-[#101817]/85 p-5"><div className="mb-4 flex items-center gap-3"><Activity className="h-5 w-5 text-[#81a684]" /><h3 className="font-display text-xl">Bitácora técnica</h3></div><div className="max-h-64 space-y-2 overflow-auto pr-1 font-mono text-xs text-[#c7b68b]">{log.map((item, index) => <div key={`${item}-${index}`} className="border-l border-[#d49b4a]/50 bg-black/20 p-3">{item}</div>)}</div></div><div className="border border-[#597060]/40 bg-[#101817]/85 p-5"><div className="mb-3 flex items-center gap-3"><BrainCircuit className="h-5 w-5 text-[#d49b4a]" /><h3 className="font-display text-xl">Síntesis IA</h3></div><p className="mb-3 font-mono text-[10px] text-[#81a684]">Endpoint: {API_BASE_URL}</p><p className="min-h-24 whitespace-pre-wrap border border-[#597060]/30 bg-black/20 p-3 text-sm leading-relaxed text-[#d2d0c7]">{aiResult || "La pestaña Expediente ya incluye narrativa local; aquí puedes probar prompts configurables sobre el informe completo."}</p></div></aside></div>
          <FindingsPanel report={findings} activeTab={activeFindingTab} setActiveTab={setActiveFindingTab} selectedEntityId={selectedEntityId} setSelectedEntityId={setSelectedEntityId} selectedTaskId={selectedTaskId} setSelectedTaskId={setSelectedTaskId} hitlDraft={hitlDraft} setHitlDraft={setHitlDraft} onCompleteTask={completeHumanTask} onRefresh={() => refreshWorkspace().catch(() => setLog((current) => ["No se pudo refrescar hallazgos.", ...current]))} onCopyReport={copyReport} />
        </section>
      </section>
    </main>
  );
}
