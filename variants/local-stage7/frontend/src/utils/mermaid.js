export function extractMermaidSource(content) {
  const source = String(content ?? '')
  const fencedBlock = source.match(/```mermaid\s*([\s\S]*?)```/i)
  if (fencedBlock) return fencedBlock[1].trim()

  const bareSource = source.trim()
  const diagramType = /^(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram|journey|gantt|pie|quadrantChart|requirementDiagram|gitGraph|mindmap|timeline|zenuml|sankey-beta|xychart-beta|block-beta|packet-beta|architecture-beta|radar-beta)\b/i
  return diagramType.test(bareSource) ? bareSource : ''
}
