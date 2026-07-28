import { nextTick, onMounted, onUnmounted, ref, watch, type ComputedRef, type Ref } from 'vue'

export function useOutlineMindmap(options: {
  viewMode: Ref<'mindmap' | 'classic'>
  outline: Ref<Record<string, any> | null>
  arcs: ComputedRef<any[]>
}) {
  const nodeRefs = ref<Record<string, HTMLElement>>({})
  const connections = ref<Array<{ d: string }>>([])

  const updateConnections = () => {
    connections.value = []
    if (options.viewMode.value !== 'mindmap' || !options.outline.value) return

    const container = document.querySelector('.mindmap-canvas')
    if (!container) return
    const containerRect = container.getBoundingClientRect()

    const links: Array<[string, string]> = [['center-node', 'branch-arcs']]

    options.arcs.value.forEach((_: any, idx: number) => {
      links.push(['branch-arcs', `arc-node-${idx}`])
    })

    links.forEach(([parentId, childId]) => {
      const parentEl = nodeRefs.value[parentId]
      const childEl = nodeRefs.value[childId]

      if (parentEl && childEl) {
        const parentRect = parentEl.getBoundingClientRect()
        const childRect = childEl.getBoundingClientRect()

        const x1 = parentRect.left + parentRect.width - containerRect.left
        const y1 = parentRect.top + parentRect.height / 2 - containerRect.top

        const x2 = childRect.left - containerRect.left
        const y2 = childRect.top + childRect.height / 2 - containerRect.top

        const dx = Math.abs(x2 - x1) * 0.45
        const pathStr = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`
        connections.value.push({ d: pathStr })
      }
    })
  }

  const scheduleConnectionUpdate = (delay = 300) => {
    nextTick(() => {
      setTimeout(updateConnections, delay)
    })
  }

  watch(options.viewMode, (mode) => {
    if (mode === 'mindmap' && options.outline.value) {
      scheduleConnectionUpdate(200)
    }
  })

  watch(
    () => options.outline.value,
    () => {
      if (options.viewMode.value === 'mindmap' && options.outline.value) {
        scheduleConnectionUpdate()
      }
    },
  )

  watch(
    options.arcs,
    () => {
      if (options.viewMode.value === 'mindmap' && options.outline.value) {
        scheduleConnectionUpdate()
      }
    },
    { deep: true },
  )

  const onResize = () => {
    updateConnections()
  }

  onMounted(() => {
    window.addEventListener('resize', onResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', onResize)
  })

  const setNodeRef = (id: string, el: Element | null) => {
    if (el) {
      nodeRefs.value[id] = el as HTMLElement
    }
  }

  return {
    nodeRefs,
    connections,
    updateConnections,
    scheduleConnectionUpdate,
    setNodeRef,
  }
}