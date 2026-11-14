import L from 'leaflet'
import * as React from 'react'
import {
  Circle,
  CircleMarker,
  ImageOverlay,
  MapContainer,
  Marker,
  Polygon,
  Polyline,
  TileLayer,
  Tooltip,
  useMapEvents,
} from 'react-leaflet'
import { CHART_COLORS, LUNAR_TILE_ATTRIBUTION, LUNAR_TILE_URL } from '@/config/app'
import { fmtLat, fmtLon } from '@/lib/format'
import { cn } from '@/lib/utils'
import { polarNightRings } from './night'
import { usePsrs } from './psr'
import { fromLeaflet, rhoForLat, toLeaflet } from './projection'
import type { LunarMapProps, Slot } from './types'

const LAT_RINGS = [-89, -88, -87, -86, -85, -84, -82, -80]
const MERIDIANS = Array.from({ length: 12 }, (_, i) => i * 30 - 180)
const OUTER = rhoForLat(-80)
const INITIAL_BOUNDS = L.latLngBounds([-OUTER, -OUTER], [OUTER, OUTER])

const MIN_CRATER_PX = 6
const MIN_LABEL_PX = 32
const SLOT_COLOR: Record<Slot, string> = { A: '#6b9cff', B: '#c79bff' }

function pinIcon(slot: Slot) {
  return L.divIcon({
    className: '',
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    html: `<div style="width:26px;height:26px;border-radius:50%;border:2px solid ${SLOT_COLOR[slot]};
      background:rgba(13,21,36,.85);color:${SLOT_COLOR[slot]};display:grid;place-items:center;
      font:600 13px 'Barlow Semi Condensed',sans-serif">${slot}</div>`,
  })
}

function textIcon(text: string, cls = '') {
  return L.divIcon({
    className: '',
    iconSize: [0, 0],
    html: `<span class="${cls}" style="position:absolute;transform:translate(-50%,-50%);white-space:nowrap;
      font-size:11px;color:${CHART_COLORS.axis}">${text}</span>`,
  })
}

function ClickPicker({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      const { lat, lon } = fromLeaflet(e.latlng.lat, e.latlng.lng)
      if (lat <= -80 && lat > -89.9999) onPick(lat, lon)
    },
  })
  return null
}

function ZoomWatcher({ onZoom }: { onZoom: (zoom: number) => void }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) })
  React.useEffect(() => onZoom(map.getZoom()), [map])
  return null
}

function CursorReadout({ onMove }: { onMove: (v: { lat: number; lon: number } | null) => void }) {
  useMapEvents({
    mousemove(e) {
      onMove(fromLeaflet(e.latlng.lat, e.latlng.lng))
    },
    mouseout() {
      onMove(null)
    },
  })
  return null
}

/**
 * 2D south-polar stereographic map (Leaflet, CRS.Simple in projected km).
 * Vector reference layers only by default; an imagery tile layer in the same
 * grid can be enabled with VITE_LUNAR_TILE_URL.
 */
const IMAGERY_BOUNDS = L.latLngBounds([-OUTER, -OUTER], [OUTER, OUTER])

export function LunarMap({
  sites, selections, activeSlot, onSelectSite, onPickCoordinates, className, imagery, onImageryError, craters, sun,
}: LunarMapProps) {
  const [zoom, setZoom] = React.useState(0)
  const { shapes: psrShapes } = usePsrs()
  const polarCraters = React.useMemo(() => (craters ?? []).filter((c) => c.latitude_deg <= -80), [craters])
  const night = React.useMemo(
    () => (sun ? polarNightRings(sun.latitude_deg, sun.longitude_deg).map((ring) => ring.map(([lat, lon]) => toLeaflet(lat, lon))) : null),
    [sun?.latitude_deg, sun?.longitude_deg],
  )
  const [cursor, setCursor] = React.useState<{ lat: number; lon: number } | null>(null)
  const [imgState, setImgState] = React.useState<'idle' | 'loading' | 'ok' | 'error'>('idle')
  React.useEffect(() => setImgState(imagery ? 'loading' : 'idle'), [imagery?.url])
  const hasImagery = Boolean(imagery) && imgState !== 'error'

  return (
    <div className={cn('relative overflow-hidden rounded-md border border-rule-soft', className)}>
      <MapContainer
        crs={L.CRS.Simple}
        bounds={INITIAL_BOUNDS}
        maxBounds={L.latLngBounds([-OUTER * 1.15, -OUTER * 1.15], [OUTER * 1.15, OUTER * 1.15])}
        minZoom={-1.5}
        maxZoom={5}
        zoomSnap={0.25}
        attributionControl={Boolean(LUNAR_TILE_URL)}
        className="h-full w-full"
        style={{ cursor: onPickCoordinates ? 'crosshair' : undefined }}
      >
        {LUNAR_TILE_URL && <TileLayer url={LUNAR_TILE_URL} attribution={LUNAR_TILE_ATTRIBUTION} noWrap />}
        {imagery?.previewUrl && <ImageOverlay key={imagery.previewUrl} url={imagery.previewUrl} bounds={IMAGERY_BOUNDS} />}
        {imagery && (
          <ImageOverlay
            key={imagery.url}
            url={imagery.url}
            bounds={IMAGERY_BOUNDS}
            eventHandlers={{
              load: () => setImgState('ok'),
              error: () => {
                setImgState('error')
                onImageryError?.(imagery.url)
              },
            }}
          />
        )}

        {LAT_RINGS.map((lat) => (
          <Circle
            key={lat}
            center={[0, 0]}
            radius={rhoForLat(lat)}
            interactive={false}
            pathOptions={{ color: CHART_COLORS.grid, weight: lat % 5 === 0 ? 1.2 : 0.8, fill: false }}
          />
        ))}
        {MERIDIANS.map((lon) => (
          <Polyline
            key={lon}
            interactive={false}
            positions={[toLeaflet(-89.0, lon), toLeaflet(-80, lon)]}
            pathOptions={{ color: CHART_COLORS.grid, weight: lon % 90 === 0 ? 1.2 : 0.7 }}
          />
        ))}
        {[-88, -86, -84, -82].map((lat) => (
          <Marker key={`l${lat}`} position={toLeaflet(lat, 135)} icon={textIcon(`${-lat}°S`)} interactive={false} />
        ))}
        {[0, 90, 180, -90].map((lon) => (
          <Marker
            key={`m${lon}`}
            position={toLeaflet(-80.6, lon)}
            icon={textIcon(lon === 0 ? '0° (Earth-facing)' : lon === 180 ? '180°' : lon > 0 ? `${lon}°E` : `${-lon}°W`)}
            interactive={false}
          />
        ))}

        {psrShapes.map(({ psr, positions }) => (
          <Polygon
            key={psr.psr_id}
            positions={positions}
            interactive={false}
            pathOptions={{ color: '#41597e', weight: 1, dashArray: '2 3', opacity: 0.65, fillColor: '#0b1526', fillOpacity: 0.45 }}
          />
        ))}

        {night && (
          <Polygon
            positions={night}
            interactive={false}
            pathOptions={{ color: CHART_COLORS.sun, weight: 1, opacity: 0.8, fillColor: '#02050a', fillOpacity: 0.5 }}
          />
        )}

        {polarCraters.map((c) => {
          // CRS.Simple: one map unit (km) is 2^zoom pixels.
          const px = c.diameter_km * 2 ** zoom
          if (px < MIN_CRATER_PX) return null
          return (
            <Circle
              key={`${c.name}:${px >= MIN_LABEL_PX}`}
              center={toLeaflet(c.latitude_deg, c.longitude_deg)}
              radius={c.diameter_km / 2}
              interactive={false}
              pathOptions={{ color: hasImagery ? '#c9d3e3' : CHART_COLORS.terrainEdge, weight: 1, dashArray: '3 3', opacity: hasImagery ? 0.55 : 1, fillColor: '#0a111d', fillOpacity: hasImagery ? 0 : 0.6 }}
            >
              {px >= MIN_LABEL_PX && (
                <Tooltip permanent direction="center" className={hasImagery ? 'crater-label crater-label-on-image' : 'crater-label'}>
                  {c.name}
                </Tooltip>
              )}
            </Circle>
          )
        })}

        {sites.map((s) => {
          const selected = Object.values(selections).some(
            (sel) => sel && Math.abs(sel.lat - s.latitude_deg) < 1e-6 && Math.abs(sel.lon - s.longitude_deg) < 1e-6,
          )
          return (
            <CircleMarker
              key={s.id}
              center={toLeaflet(s.latitude_deg, s.longitude_deg)}
              radius={selected ? 0 : 6}
              pathOptions={{ color: '#e4eaf4', weight: 1.5, fillColor: '#e4eaf4', fillOpacity: 0.85 }}
              eventHandlers={{
                click: (e) => {
                  L.DomEvent.stopPropagation(e)
                  onSelectSite(s, activeSlot)
                },
              }}
            >
              <Tooltip direction="right" offset={[10, 0]} className="lunanav-tip">
                {s.name}
              </Tooltip>
            </CircleMarker>
          )
        })}

        {(Object.entries(selections) as [Slot, LunarMapProps['selections'][Slot]][]).map(
          ([slot, sel]) =>
            sel && (
              <Marker key={slot} position={toLeaflet(sel.lat, sel.lon)} icon={pinIcon(slot)} interactive={false}>
                <Tooltip permanent direction="right" offset={[14, 0]} className="lunanav-tip">
                  {sel.label}
                </Tooltip>
              </Marker>
            ),
        )}

        {onPickCoordinates && <ClickPicker onPick={(lat, lon) => onPickCoordinates(lat, lon, activeSlot)} />}
        <ZoomWatcher onZoom={setZoom} />
        <CursorReadout onMove={setCursor} />
      </MapContainer>

      <div className="pointer-events-none absolute right-2 bottom-2 z-[500] rounded bg-night/85 px-2 py-1 text-xs text-muted num">
        {cursor && cursor.lat <= -80 ? `${fmtLat(cursor.lat)}  ${fmtLon(cursor.lon)}` : 'South polar stereographic'}
      </div>
      <div className="pointer-events-none absolute left-2 bottom-2 z-[500] max-w-[62%] rounded bg-night/85 px-2 py-1 text-[11px] leading-snug text-faint">
        {imagery && imgState === 'ok' && `${imagery.credit} Shadows in the image were captured by LRO; the shaded area is the night side.`}
        {imagery && imgState === 'loading' && 'Loading sharp imagery from NASA/JPL Moon Trek… (first load can take a minute)'}
        {imagery && imgState === 'error' && 'Imagery unavailable. Showing reference outlines only.'}
        {!imagery && !LUNAR_TILE_URL && 'Reference map: graticule, shaded PSR polygons and IAU crater outlines.'}
        {psrShapes.length > 0 && 'Shaded polygons: permanently shadowed regions (LROC, >5 km²).'}
      </div>
    </div>
  )
}
