/**
 * Diseño seleccionado: Cartografía forense neo-brutalista chilena.
 * La página funciona como mesa de análisis: panel izquierdo para semillas y transforms,
 * lienzo de grafo dominante, bitácora inferior y señales claras para evidencias/HITL.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Activity, AlertTriangle, BrainCircuit, Database, Fingerprint, GitBranch, LockKeyhole, Network, Play, Search, ShieldCheck } from "lucide-react";
import { api, API_BASE_URL, type GraphEdge, type GraphNode, type Transform } from "@/lib/api";
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

function nodeColor(type: string) {
  if (type === "HumanTask") return "#d49b4a";
  if (type === "DorkQuery") return "#81a684";
  if (type === "Seed") return "#e6c27a";
  if (type === "Vehicle") return "#b76f52";
  if (type === "Phone") return "#6fa8a1";
  if (type === "Domain") return "#9db887";
  return "#d2d0c7";
}

function toFlowNodes(nodes: GraphNode[]): Node[] {
  return nodes.map((node, index) => ({
    id: node.id,
    position: { x: 140 + (index % 4) * 210, y: 110 + Math.floor(index / 4) * 150 },
    data: { label: `${node.type}\n${node.label}` },
    style: {
      background: "rgba(13, 18, 17, 0.94)",
      border: `1px solid ${nodeColor(node.type)}`,
      color: "#f1ead9",
      width: 172,
      minHeight: 68,
      fontFamily: "IBM Plex Mono, monospace",
      fontSize: 11,
      whiteSpace: "pre-line",
      boxShadow: `0 0 24px ${nodeColor(node.type)}26`,
    },
  }));
}

function toFlowEdges(edges: GraphEdge[]): Edge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.type,
    animated: edge.type === "REQUIRES_HUMAN" || edge.type === "INFERRED_LINK",
    style: { stroke: edge.type === "REQUIRES_HUMAN" ? "#d49b4a" : "#6f8f7d", strokeWidth: 1.8 },
    labelStyle: { fill: "#c7b68b", fontFamily: "IBM Plex Mono, monospace", fontSize: 10 },
  }));
}

export default function Home() {
  const [health, setHealth] = useState<string>("conectando");
  const [transforms, setTransforms] = useState<Transform[]>([]);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [inputType, setInputType] = useState("rut");
  const [value, setValue] = useState("12.345.678-5");
  const [selectedTransform, setSelectedTransform] = useState("cl.rut.normalize");
  const [log, setLog] = useState<string[]>(["Estación OSINT inicializada. Conectores restringidos se abrirán como tareas human-in-the-loop."]);
  const [aiResult, setAiResult] = useState("");

  const investigationId = "demo";

  const refreshGraph = useCallback(async () => {
    const graph = await api.graph(investigationId);
    setGraphNodes(graph.nodes);
    setGraphEdges(graph.edges);
  }, []);

  useEffect(() => {
    api.health().then((data) => setHealth(`${data.status} · ${data.ai_provider}`)).catch(() => setHealth("api offline"));
    api.transforms().then((items) => {
      setTransforms(items);
      setSelectedTransform(items[0]?.id || "cl.rut.normalize");
    }).catch(() => setLog((current) => ["No se pudo cargar catálogo de transforms.", ...current]));
    refreshGraph().catch(() => undefined);
  }, [refreshGraph]);

  const availableTransforms = useMemo(() => transforms.filter((transform) => transform.input_types.includes(inputType) || transform.id.startsWith("cl.dork") || transform.id.includes("human")), [transforms, inputType]);
  const flowNodes = useMemo(() => toFlowNodes(graphNodes), [graphNodes]);
  const flowEdges = useMemo(() => toFlowEdges(graphEdges), [graphEdges]);

  async function addSeed() {
    await api.addSeed({ investigation_id: investigationId, input_type: inputType, value });
    setLog((current) => [`Semilla agregada: ${inputType}=${value}`, ...current]);
    await refreshGraph();
  }

  async function runTransform() {
    try {
      const result = await api.runTransform({ investigation_id: investigationId, transform_id: selectedTransform, input_type: inputType, value });
      setLog((current) => [`Transform ejecutado: ${selectedTransform} · entidades: ${result.created_entities.length}`, ...current]);
      await refreshGraph();
    } catch (error) {
      setLog((current) => [`Error transform: ${(error as Error).message}`, ...current]);
    }
  }

  async function runAiSummary() {
    try {
      const result = await api.aiRun({ prompt_id: "semantic_summary", variables: { evidence: graphNodes.map((node) => `${node.type}: ${node.label}`).join("\n") }, provider: "mock" });
      setAiResult(result.content);
      setLog((current) => ["Síntesis IA solicitada con proveedor mock/configurable.", ...current]);
    } catch (error) {
      setLog((current) => [`Error IA: ${(error as Error).message}`, ...current]);
    }
  }

  return (
    <main className="min-h-screen bg-[#0a0f0e] text-[#f1ead9] selection:bg-[#d49b4a]/30" style={{ backgroundImage: `linear-gradient(90deg, rgba(10,15,14,.96), rgba(10,15,14,.82)), url(${HERO_URL})`, backgroundSize: "cover", backgroundAttachment: "fixed" }}>
      <section className="grid min-h-screen grid-cols-1 xl:grid-cols-[380px_1fr]">
        <aside className="border-r border-[#597060]/35 bg-[#0b1110]/90 p-6 backdrop-blur-xl">
          <div className="mb-8 flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center border border-[#d49b4a] bg-[#d49b4a]/10 shadow-[0_0_34px_rgba(212,155,74,.22)]">
              <Network className="h-6 w-6 text-[#d49b4a]" />
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.34em] text-[#81a684]">OSINT Chile</p>
              <h1 className="font-display text-2xl font-semibold tracking-tight">Graph Workbench</h1>
            </div>
          </div>

          <div className="mb-6 grid grid-cols-3 gap-2 text-xs">
            <div className="border border-[#597060]/40 bg-black/20 p-3"><Database className="mb-2 h-4 w-4 text-[#81a684]" />PostgreSQL</div>
            <div className="border border-[#597060]/40 bg-black/20 p-3"><GitBranch className="mb-2 h-4 w-4 text-[#d49b4a]" />Neo4j</div>
            <div className="border border-[#597060]/40 bg-black/20 p-3"><BrainCircuit className="mb-2 h-4 w-4 text-[#c7b68b]" />Ollama</div>
          </div>

          <div className="mb-6 border border-[#597060]/40 bg-[#101817]/80 p-4 shadow-[0_18px_60px_rgba(0,0,0,.25)]">
            <div className="mb-4 flex items-center justify-between">
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#81a684]">Semilla</span>
              <span className="border border-[#597060]/40 px-2 py-1 font-mono text-[10px] text-[#c7b68b]">API {health}</span>
            </div>
            <label className="mb-2 block text-sm text-[#d2d0c7]">Tipo de dato inicial</label>
            <select value={inputType} onChange={(event) => setInputType(event.target.value)} className="mb-3 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-sm outline-none focus:border-[#d49b4a]">
              {inputTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <label className="mb-2 block text-sm text-[#d2d0c7]">Valor</label>
            <input value={value} onChange={(event) => setValue(event.target.value)} className="mb-4 w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-sm outline-none focus:border-[#d49b4a]" />
            <div className="grid grid-cols-2 gap-3">
              <Button onClick={addSeed} className="rounded-none bg-[#597060] text-[#f1ead9] hover:bg-[#6f8f7d]"><Fingerprint className="mr-2 h-4 w-4" />Agregar</Button>
              <Button onClick={runTransform} className="rounded-none bg-[#d49b4a] text-[#16110b] hover:bg-[#e6c27a]"><Play className="mr-2 h-4 w-4" />Ejecutar</Button>
            </div>
          </div>

          <div className="mb-6 border border-[#597060]/40 bg-[#101817]/80 p-4">
            <label className="mb-2 block text-sm text-[#d2d0c7]">Transform</label>
            <select value={selectedTransform} onChange={(event) => setSelectedTransform(event.target.value)} className="w-full border border-[#597060]/50 bg-[#0a0f0e] px-3 py-3 font-mono text-xs outline-none focus:border-[#d49b4a]">
              {availableTransforms.map((transform) => <option key={transform.id} value={transform.id}>{transform.id}</option>)}
            </select>
            <div className="mt-4 max-h-52 space-y-2 overflow-auto pr-1">
              {availableTransforms.slice(0, 5).map((transform) => (
                <div key={transform.id} className="border border-[#597060]/30 bg-black/20 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-[11px] text-[#e6c27a]">{transform.name}</p>
                    {transform.requires_human ? <LockKeyhole className="h-4 w-4 text-[#d49b4a]" /> : <ShieldCheck className="h-4 w-4 text-[#81a684]" />}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-[#a9b5a6]">{transform.description}</p>
                </div>
              ))}
            </div>
          </div>

          <button onClick={runAiSummary} className="group w-full border border-[#d49b4a]/60 bg-[#d49b4a]/10 p-4 text-left transition hover:bg-[#d49b4a]/18">
            <div className="flex items-center gap-3">
              <BrainCircuit className="h-5 w-5 text-[#d49b4a]" />
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-[#d49b4a]">IA configurable</p>
                <p className="text-sm text-[#f1ead9]">Sintetizar grafo con prompt editable</p>
              </div>
            </div>
          </button>
        </aside>

        <section className="flex min-h-screen flex-col">
          <header className="border-b border-[#597060]/35 bg-[#0b1110]/70 px-8 py-6 backdrop-blur-xl">
            <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
              <div>
                <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.34em] text-[#81a684]">Cartografía forense · fuentes públicas/autorizadas · HITL</p>
                <h2 className="max-w-4xl font-display text-4xl font-semibold leading-tight text-[#f1ead9] md:text-6xl">De una semilla chilena a un grafo de evidencia trazable.</h2>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center font-mono text-xs">
                <div className="border border-[#597060]/40 bg-black/25 p-3"><strong className="block text-xl text-[#e6c27a]">{graphNodes.length}</strong>Nodos</div>
                <div className="border border-[#597060]/40 bg-black/25 p-3"><strong className="block text-xl text-[#81a684]">{graphEdges.length}</strong>Relaciones</div>
                <div className="border border-[#597060]/40 bg-black/25 p-3"><strong className="block text-xl text-[#d49b4a]">{transforms.length}</strong>Transforms</div>
              </div>
            </div>
          </header>

          <div className="grid flex-1 grid-cols-1 gap-5 p-5 2xl:grid-cols-[1fr_360px]">
            <div className="relative min-h-[620px] overflow-hidden border border-[#597060]/40 bg-[#0b1110]/82 shadow-[0_28px_90px_rgba(0,0,0,.36)]">
              <div className="absolute inset-0 opacity-20" style={{ backgroundImage: `url(${GRAPH_PANEL_URL})`, backgroundSize: "cover", backgroundPosition: "center" }} />
              <div className="absolute inset-0 bg-[linear-gradient(rgba(129,166,132,.06)_1px,transparent_1px),linear-gradient(90deg,rgba(129,166,132,.06)_1px,transparent_1px)] bg-[size:42px_42px]" />
              <div className="relative h-full min-h-[620px]">
                {flowNodes.length === 0 ? (
                  <div className="grid h-full min-h-[620px] place-items-center p-8 text-center">
                    <div className="max-w-lg border border-[#597060]/40 bg-[#0b1110]/86 p-8">
                      <Search className="mx-auto mb-4 h-10 w-10 text-[#d49b4a]" />
                      <h3 className="mb-3 font-display text-2xl">Agrega una semilla para iniciar el expediente gráfico</h3>
                      <p className="text-[#a9b5a6]">RUT, email .cl, teléfono, patente, dominio, nombre o empresa pueden convertirse en nodos iniciales.</p>
                    </div>
                  </div>
                ) : (
                  <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
                    <Background color="#597060" gap={28} size={1} />
                    <Controls />
                    <MiniMap nodeColor={(node: Node) => String(node.style?.border || "#d49b4a").replace("1px solid ", "")} pannable zoomable />
                  </ReactFlow>
                )}
              </div>
            </div>

            <aside className="space-y-5">
              <div className="border border-[#597060]/40 bg-[#101817]/85 p-5">
                <div className="mb-4 flex items-center gap-3"><AlertTriangle className="h-5 w-5 text-[#d49b4a]" /><h3 className="font-display text-xl">Human-in-the-loop</h3></div>
                <img src={HUMAN_LOOP_URL} alt="Representación abstracta de tareas human-in-the-loop" className="mb-4 h-44 w-full object-cover opacity-80" />
                <p className="text-sm leading-relaxed text-[#a9b5a6]">Las fuentes con login, CAPTCHA, validación manual o restricciones no se automatizan. Se registran como compuertas de investigación con instrucciones, fuente y evidencia esperada.</p>
              </div>

              <div className="border border-[#597060]/40 bg-[#101817]/85 p-5">
                <div className="mb-4 flex items-center gap-3"><Activity className="h-5 w-5 text-[#81a684]" /><h3 className="font-display text-xl">Bitácora</h3></div>
                <div className="max-h-64 space-y-2 overflow-auto pr-1 font-mono text-xs text-[#c7b68b]">
                  {log.map((item, index) => <div key={`${item}-${index}`} className="border-l border-[#d49b4a]/50 bg-black/20 p-3">{item}</div>)}
                </div>
              </div>

              <div className="border border-[#597060]/40 bg-[#101817]/85 p-5">
                <div className="mb-3 flex items-center gap-3"><BrainCircuit className="h-5 w-5 text-[#d49b4a]" /><h3 className="font-display text-xl">Síntesis IA</h3></div>
                <p className="mb-3 font-mono text-[10px] text-[#81a684]">Endpoint: {API_BASE_URL}</p>
                <p className="min-h-24 whitespace-pre-wrap border border-[#597060]/30 bg-black/20 p-3 text-sm leading-relaxed text-[#d2d0c7]">{aiResult || "Ejecuta una síntesis para probar prompts configurables. Por defecto se usa modo mock en la UI; el backend soporta Ollama y APIs externas."}</p>
              </div>
            </aside>
          </div>
        </section>
      </section>
    </main>
  );
}
