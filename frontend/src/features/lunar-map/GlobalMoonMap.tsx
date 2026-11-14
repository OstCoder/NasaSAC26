import L from 'leaflet'
import * as React from 'react'
import { CircleMarker, MapContainer, Polygon, Polyline, TileLayer, Tooltip, useMapEvents } from 'react-leaflet'
import { CHART_COLORS } from '@/config/app'
import { fmtLat, fmtLon } from '@/lib/format'
import { cn } from '@/lib/utils'
import { craterRing } from './craterRing'
import { nightPolygon } from './night'
import type { GlobalMoonMapProps } from './types'

const WORLD = L.latLngBounds([-90, -180], [90, 180])
const PARALLELS = [-60, -30, 0, 30, 60]
const MERIDIANS = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150]
const KM_PER_DEG = 30.32
const MIN_CRATER_PX = 12
const MIN_LABEL_PX = 18
const MAX_LABELS = 40
const GRID = { color: '#c9d3e3', weight: 0.6, opacity: 0.25 }

function ViewWatcher({ onView }: { onView: (v: { zoom: number; bounds: L.LatLngBounds }) => void }) {
  const update = () => onView({ zoom: map.getZoom(), bounds: map.getBounds() })
  const map = useMapEvents({ moveend: update, zoomend: update })
  React.useEffect(update, [map])
  return null
}

function CursorReadout({ onMove }: { onMove: (v: L.LatLng | null) => void }) {
  useMapEvents({
    mousemove: (e) => onMove(e.latlng),
    mouseout: () => onMove(null),
  })
  return null
}

/**
 * Whole Moon, equirectangular. EPSG4326 has the same tile layout as Moon Trek's
 * (level 0 is 2x1 tiles, row 0 at the north edge), so Leaflet asks for the right
 * tiles, and LatLng here is real selenographic degrees, unlike the polar map.
 */
export function GlobalMoonMap({ sites, selection, onSelectSite, tiles, sun, earth, craters, onImageryError, className }: GlobalMoonMapProps) {
  const [view, setView] = React.useState<{ zoom: number; bounds: L.LatLngBounds } | null>(null)
  // Craters big enough to see in the current view, largest first. Only the largest few get labels.
  const shown = React.useMemo(() => {
    if (!view || !craters) return []
    const pxPerKm = (256 * 2 ** view.zoom) / 180 / KM_PER_DEG
    return craters
      .map((c) => ({ c, px: c.diameter_km * pxPerKm }))
      .filter(({ c, px }) => px >= MIN_CRATER_PX && view.bounds.contains([c.latitude_deg, c.longitude_deg]))
      .sort((a, b) => b.px - a.px)
  }, [view, craters])
  const [cursor, setCursor] = React.useState<L.LatLng | null>(null)
  const [imgState, setImgState] = React.useState<'idle' | 'loading' | 'ok' | 'error'>('idle')
  React.useEffect(() => setImgState(tiles ? 'loading' : 'idle'), [tiles?.url])
  const night = React.useMemo(
    () => (sun ? nightPolygon(sun.latitude_deg, sun.longitude_deg) : null),
    [sun?.latitude_deg, sun?.longitude_deg],
  )

  return (
    <div className={cn('relative overflow-hidden rounded-md border border-rule-soft bg-[#070c15]', className)}>
      <MapContainer
        crs={L.CRS.EPSG4326}
        bounds={WORLD.pad(0.05)}
        maxBounds={WORLD.pad(0.1)}
        preferCanvas
        minZoom={-1}
        maxZoom={(tiles?.maxNativeZoom ?? 6) + 1}
        zoomSnap={0}
        attributionControl={false}
        className="h-full w-full"
      >
        {tiles && (
          <TileLayer
            key={tiles.url}
            url={tiles.url}
            bounds={WORLD}
            noWrap
            maxNativeZoom={tiles.maxNativeZoom}
            eventHandlers={{
              tileload: () => setImgState('ok'),
              tileerror: (e) => {
                setImgState((s) => (s === 'ok' ? s : 'error'))
                onImageryError?.((e.tile as HTMLImageElement).src)
              },
            }}
          />
        )}

        {PARALLELS.map((lat) => (
          <Polyline key={lat} interactive={false} positions={[[lat, -180], [lat, 180]]} pathOptions={GRID} />
        ))}
        {MERIDIANS.map((lon) => (
          <Polyline key={lon} interactive={false} positions={[[-90, lon], [90, lon]]} pathOptions={GRID} />
        ))}

        {night && (
          <Polygon
            positions={night}
            interactive={false}
            pathOptions={{ color: CHART_COLORS.sun, weight: 1, opacity: 0.7, fillColor: '#02050a', fillOpacity: 0.55 }}
          />
        )}
        {shown.map(({ c, px }, i) => {
          const labelled = px >= MIN_LABEL_PX && i < MAX_LABELS
          return (
            <Polygon
              key={`${c.name}:${labelled}`}
              positions={craterRing(c.latitude_deg, c.longitude_deg, c.diameter_km)}
              interactive={false}
              smoothFactor={0}
              pathOptions={{ color: '#c9d3e3', weight: 1, opacity: 0.55, fill: false }}
            >
              {labelled && (
                <Tooltip permanent direction="center" className="crater-label crater-label-on-image">{c.name}</Tooltip>
              )}
            </Polygon>
          )
        })}

        {sun && (
          <CircleMarker center={[sun.latitude_deg, sun.longitude_deg]} radius={6}
            pathOptions={{ color: '#fff', weight: 1, fillColor: CHART_COLORS.sun, fillOpacity: 1 }}>
            <Tooltip direction="right" offset={[8, 0]} className="lunanav-tip">Sun directly overhead here</Tooltip>
          </CircleMarker>
        )}
        {earth && (
          <CircleMarker center={[earth.latitude_deg, earth.longitude_deg]} radius={6}
            pathOptions={{ color: '#fff', weight: 1, fillColor: CHART_COLORS.earth, fillOpacity: 1 }}>
            <Tooltip direction="right" offset={[8, 0]} className="lunanav-tip">Earth directly overhead here</Tooltip>
          </CircleMarker>
        )}

        {sites.map((s) => (
          <CircleMarker
            key={s.id}
            center={[s.latitude_deg, s.longitude_deg]}
            radius={4}
            pathOptions={{ color: '#e4eaf4', weight: 1.5, fillColor: '#e4eaf4', fillOpacity: 0.85 }}
            eventHandlers={{
              click: (e) => {
                L.DomEvent.stopPropagation(e)
                onSelectSite(s)
              },
            }}
          >
            <Tooltip direction="right" offset={[8, 0]} className="lunanav-tip">{s.name}</Tooltip>
          </CircleMarker>
        ))}
        {selection && (
          <CircleMarker center={[selection.lat, selection.lon]} radius={7} interactive={false}
            pathOptions={{ color: CHART_COLORS.cursor, weight: 2, fill: false }} />
        )}
        <ViewWatcher onView={setView} />
        <CursorReadout onMove={setCursor} />
      </MapContainer>

      <div className="pointer-events-none absolute right-2 bottom-2 z-[500] rounded bg-night/85 px-2 py-1 text-xs text-muted num">
        {cursor ? `${fmtLat(cursor.lat)}  ${fmtLon(cursor.lng)}` : 'Equirectangular'}
      </div>
      <div className="pointer-events-none absolute left-2 bottom-2 z-[500] max-w-[62%] rounded bg-night/85 px-2 py-1 text-[11px] leading-snug text-faint">
        {tiles && imgState === 'ok' && tiles.credit}
        {tiles && imgState === 'loading' && 'Loading imagery from NASA/JPL Moon Trek…'}
        {tiles && imgState === 'error' && 'Imagery unavailable. Showing the grid only.'}
        {!tiles && 'Imagery off.'}
      </div>
    </div>
  )
}
