/** Data shape emitted by PresetSelector (composable preset system). */
export interface Composition {
  channel: string
  theme: string
  /** Human-readable preset name; `theme` remains the stable internal id. */
  theme_label?: string
  mechanisms: string[]
  cool_points: string[]
}
