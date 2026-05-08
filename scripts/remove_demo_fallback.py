from pathlib import Path

path = Path('/home/ubuntu/osint-chile-graph/client/src/pages/Home.tsx')
text = path.read_text()
start = text.index('const demoNodes: GraphNode[] = [')
end = text.index('\nfunction buildMarkdownReport', start)
replacement = '''function createUnavailableReport(): FindingsReport {
  return {
    investigation: {
      id: "api-unavailable",
      title: "API no disponible — sin evidencia OSINT cargada",
      objective: "La interfaz no mostrará datos ficticios. Levanta la API y ejecuta transformaciones para obtener evidencia verificable o tareas HITL reales.",
      status: "api_unavailable",
    },
    summary: {
      entities: 0,
      relationships: 0,
      evidence: 0,
      human_tasks: 0,
      pending_human_tasks: 0,
      transform_runs: 0,
      average_confidence: 0,
      entity_types: {},
      evidence_by_source: {},
    },
    analysis: {
      mode: "api_unavailable",
      executive_summary: "No hay expediente cargado porque la API no respondió. Para evitar una máscara falsa de OSINT, esta vista queda vacía hasta recibir evidencias reales, registros locales declarados o tareas humanas generadas por el backend.",
      key_findings: ["Sin evidencia OSINT real cargada en esta sesión."],
      gaps: ["Levantar backend y ejecutar transformaciones contra fuentes autorizadas.", "Completar tareas HITL para fuentes que no permitan automatización responsable."],
      recommended_next_steps: ["Verificar Docker Compose/API local.", "Agregar una semilla real y ejecutar una transformación.", "Revisar estados de fuente y capturar evidencia humana cuando corresponda."],
      entity_type_distribution: {},
      ai_status: "No se generó narrativa AI sobre datos ficticios.",
    },
    entities: [],
    entity_profiles: [],
    relationships: [],
    evidence: [],
    human_tasks: [],
    runs: [],
    timeline: [{ at: new Date().toISOString(), kind: "api_unavailable", title: "API no disponible", detail: "No se cargaron datos demostrativos ni evidencia falsa.", confidence: 0 }],
    visualizations: { treemap: [], sankey: { nodes: [], links: [] }, semantic_clusters: [] },
  };
}
'''
text = text[:start] + replacement + text[end:]
text = text.replace('const demo = createDemoReport();\n      setFindings(demo);\n      if (!selectedEntityId && demo.entity_profiles?.[0]) setSelectedEntityId(demo.entity_profiles[0].entity.id);\n      if (!selectedTaskId && demo.human_tasks?.[0]) setSelectedTaskId(demo.human_tasks[0].id);', 'const unavailable = createUnavailableReport();\n      setFindings(unavailable);\n      setSelectedEntityId(null);\n      setSelectedTaskId(null);')
text = text.replace('      setGraphNodes(demoNodes);\n      setGraphEdges(demoEdges);', '      setGraphNodes([]);\n      setGraphEdges([]);')
text = text.replace('api.health().then((data) => setHealth(`${data.status} · ${data.ai_provider}`)).catch(() => setHealth("api offline · demo local"));', 'api.health().then((data) => setHealth(`${data.status} · ${data.ai_provider}`)).catch(() => setHealth("api offline · sin datos"));')
text = text.replace('setLog((current) => ["API no disponible: usando catálogo demo local para previsualizar expediente.", ...current]);', 'setLog((current) => ["API no disponible: no se muestran datos ficticios; levanta el backend para ejecutar OSINT real.", ...current]);')
text = text.replace('description: "Transformación demo disponible cuando la API no está levantada."', 'description: "API no disponible: catálogo informativo, no ejecuta OSINT sin backend."')
path.write_text(text)
