/**
 * Public surface of the map feature. To swap in a 3D terrain view, implement
 * LunarMapProps in a new component and export it here as LunarMap (or switch on
 * the `experimental_3d_terrain` feature flag at the call site).
 */
export { LunarMap } from './LunarMap'
export type { LunarMapProps, MapSelection, Slot } from './types'
export { project, unproject, toLeaflet, fromLeaflet } from './projection'
