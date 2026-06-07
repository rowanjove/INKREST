import { computed, ref, type ComputedRef, type Ref } from 'vue'

export const GRAPH_MIN_WIDTH = 880
export const GRAPH_MIN_HEIGHT = 520
/** 圆点半径；连线和布局按此留白 */
export const NODE_CIRCLE_R = 22
export const NODE_EDGE_PAD = NODE_CIRCLE_R + 8
/** 相邻节点圆心最小弧长间距 */
export const MIN_NODE_ARC_GAP = 96

export type RelationPolarity = 'forward' | 'neutral' | 'reverse'

export type GraphNode = {
  id: string
  name: string
  location: string
  emotion: string
  x: number
  y: number
}

export type GraphEdge = {
  raw: any
  id: number | string
  sourceId: string
  targetId: string
  relation_type: string
  intensity: number
  description: string
  since_chapter: number
  polarity: RelationPolarity
  typeColor: string
  polarityColor: string
  x1: number
  y1: number
  x2: number
  y2: number
  midX: number
  midY: number
  label: string
}

export const RELATION_TYPE_COLORS: Record<string, string> = {
  结盟: '#2563eb',
  合作: '#0891b2',
  师徒: '#c66f4f',
  同门: '#0d9488',
  亲属: '#7c3aed',
  恋人: '#db2777',
  暗恋: '#ec4899',
  敌对: '#dc2626',
  反目: '#b91c1c',
  竞争: '#ea580c',
}

export function polarityFromIntensity(intensity: number): RelationPolarity {
  if (intensity > 0.15) return 'forward'
  if (intensity < -0.15) return 'reverse'
  return 'neutral'
}

export function polarityColor(polarity: RelationPolarity): string {
  if (polarity === 'forward') return '#16a34a'
  if (polarity === 'reverse') return '#dc2626'
  return '#94a3b8'
}

export function colorForRelationType(type: string): string {
  const key = (type || '').trim()
  if (key && RELATION_TYPE_COLORS[key]) return RELATION_TYPE_COLORS[key]
  let hash = 0
  for (let i = 0; i < key.length; i++) hash = key.charCodeAt(i) + ((hash << 5) - hash)
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 52%, 42%)`
}

function resolveCharacterId(key: string, charList: { id: string; name: string }[]): string | null {
  if (!key) return null
  if (charList.some((c) => c.id === key)) return key
  const byName = charList.find((c) => c.name === key)
  return byName?.id ?? key
}

export function truncateGraphName(name: string, maxLen = 4): string {
  const s = (name || '').trim()
  if (s.length <= maxLen) return s
  return `${s.slice(0, maxLen)}…`
}

function layoutRadiusForCount(n: number, maxR: number): number {
  if (n <= 1) return 0
  const byGap = MIN_NODE_ARC_GAP / (2 * Math.sin(Math.PI / n))
  return Math.min(maxR, Math.max(118, byGap))
}

function edgeLinePoints(sx: number, sy: number, tx: number, ty: number, pad = NODE_EDGE_PAD) {
  const dx = tx - sx
  const dy = ty - sy
  const dist = Math.sqrt(dx * dx + dy * dy) || 1
  const ux = dx / dist
  const uy = dy / dist
  return {
    x1: sx + ux * pad,
    y1: sy + uy * pad,
    x2: tx - ux * pad,
    y2: ty - uy * pad,
    midX: (sx + tx) / 2,
    midY: (sy + ty) / 2,
  }
}

export function useStateRelationGraph(options: {
  chronicleSource: ComputedRef<Record<string, any>>
  relations: Ref<any[]>
}) {
  const { chronicleSource, relations } = options

  const characters = computed(() => {
    const chars = chronicleSource.value?.characters
    if (!chars) return []
    return Object.entries(chars).map(([id, d]: any) => ({
      id,
      name: d.name || id,
      location: d.location || '',
      emotion: d.emotion || '',
    }))
  })

  const graphLayout = computed(() => {
    const charList = characters.value
    const rels = relations.value
    const nodeIds = new Set<string>()

    for (const c of charList) nodeIds.add(c.id)
    for (const r of rels) {
      if (r.source_char) nodeIds.add(resolveCharacterId(r.source_char, charList) || r.source_char)
      if (r.target_char) nodeIds.add(resolveCharacterId(r.target_char, charList) || r.target_char)
    }

    const nodes: GraphNode[] = Array.from(nodeIds).map((id) => {
      const fromChar = charList.find((c) => c.id === id || c.name === id)
      return {
        id: fromChar?.id ?? id,
        name: fromChar?.name ?? id,
        location: fromChar?.location ?? '',
        emotion: fromChar?.emotion ?? '',
        x: 0,
        y: 0,
      }
    })

    const n = nodes.length
    const footprint = NODE_CIRCLE_R + 10
    const maxR = Math.min(GRAPH_MIN_WIDTH, GRAPH_MIN_HEIGHT) / 2 - footprint - 28
    const radius = layoutRadiusForCount(n, maxR)
    const canvasPad = 52
    const width = Math.max(GRAPH_MIN_WIDTH, 2 * (radius + footprint) + canvasPad * 2)
    const height = Math.max(GRAPH_MIN_HEIGHT, 2 * (radius + footprint) + canvasPad * 2)
    const cx = width / 2
    const cy = height / 2
    nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, n) - Math.PI / 2
      node.x = cx + radius * Math.cos(angle)
      node.y = cy + radius * Math.sin(angle)
    })

    const nodeMap = new Map(nodes.map((nd) => [nd.id, nd]))
    const edges: GraphEdge[] = []

    for (const r of rels) {
      const sourceId = resolveCharacterId(r.source_char, charList)
      const targetId = resolveCharacterId(r.target_char, charList)
      if (!sourceId || !targetId || sourceId === targetId) continue
      const source = nodeMap.get(sourceId)
      const target = nodeMap.get(targetId)
      if (!source || !target) continue

      const intensity = Number(r.intensity ?? 0)
      const polarity = polarityFromIntensity(intensity)
      const pts = edgeLinePoints(source.x, source.y, target.x, target.y)
      const relationType = r.relation_type || '未命名'
      const polarityLabel =
        polarity === 'forward' ? '正向' : polarity === 'reverse' ? '反向' : '中立'

      edges.push({
        raw: r,
        id: r.id ?? `${sourceId}-${targetId}-${relationType}`,
        sourceId,
        targetId,
        relation_type: relationType,
        intensity,
        description: r.description || '',
        since_chapter: r.since_chapter || 1,
        polarity,
        typeColor: colorForRelationType(relationType),
        polarityColor: polarityColor(polarity),
        ...pts,
        label: `${relationType} · ${polarityLabel} (${intensity >= 0 ? '+' : ''}${intensity.toFixed(1)})`,
      })
    }

    return { nodes, edges, hasEdges: edges.length > 0, width, height }
  })

  const graphViewport = computed(() => ({
    width: graphLayout.value.width || GRAPH_MIN_WIDTH,
    height: graphLayout.value.height || GRAPH_MIN_HEIGHT,
  }))

  const hoveredEdge = ref<GraphEdge | null>(null)
  const edgeTooltipStyle = ref({ left: '0px', top: '0px' })

  const showEdgeTooltip = (edge: GraphEdge, event: MouseEvent) => {
    hoveredEdge.value = edge
    const wrap = (event.currentTarget as Element)?.closest?.('.svg-wrapper') as HTMLElement | null
    if (!wrap) return
    const rect = wrap.getBoundingClientRect()
    edgeTooltipStyle.value = {
      left: `${event.clientX - rect.left + 12}px`,
      top: `${event.clientY - rect.top + 12}px`,
    }
  }

  const hideEdgeTooltip = () => {
    hoveredEdge.value = null
  }

  const graphNodes = computed(() => graphLayout.value.nodes)
  const graphEdges = computed(() => graphLayout.value.edges)
  const graphHasRenderableNodes = computed(() => graphNodes.value.length > 0)

  return {
    characters,
    graphLayout,
    graphViewport,
    graphNodes,
    graphEdges,
    graphHasRenderableNodes,
    hoveredEdge,
    edgeTooltipStyle,
    showEdgeTooltip,
    hideEdgeTooltip,
    truncateGraphName,
  }
}