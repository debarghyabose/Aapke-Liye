// src/components/LiveMap.tsx
// Officials' live map: claim points from Member 3's photo checks (coloured by damage),
// the satellite flood extent (Copernicus EMS), and a summary + fraud-flag strip.
// Data comes through Member 2 (GET /staff/dashboard/*), staff key required.
import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getDashboard, errorText } from '../api/client';

interface Props {
  onSelectClaim: (claimId: string) => void;
  refreshKey: number; // bump to reload (e.g. after the staff key is entered)
}

const FLAG_TEXT: Record<string, string> = {
  duplicate_photo: 'Same photo in another claim',
  gps_mismatch: 'Photo taken far from the phone',
  not_genuine_photo: 'May not be a real photo',
  possible_same_house: 'Another claim from the same house',
  phone_many_claims: 'One phone behind many claims',
  outside_flood_extent: 'Outside the satellite flood map',
  no_building_at_location: 'No building at this spot on the map',
  crop_no_vegetation_before: 'No crop seen there before',
  crop_unchanged_after: 'Crop looks unchanged by satellite',
  crop_satellite_mismatch: 'Crop loss not seen by satellite',
  outside_disaster_area: 'Outside the disaster area',
  no_location: 'No location',
};
function colour(score: number): string {
  if (score >= 70) return '#C0392B';
  if (score >= 40) return '#E3A72F';
  return '#3E6B48';
}

export const LiveMap: React.FC<Props> = ({ onSelectClaim, refreshKey }) => {
  const box = useRef<HTMLDivElement | null>(null);
  const map = useRef<L.Map | null>(null);
  const layers = useRef<L.LayerGroup | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [flags, setFlags] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  // The parent's handler changes every render; keep the latest without reloading the map.
  const select = useRef(onSelectClaim);
  select.current = onSelectClaim;

  useEffect(() => {
    if (!box.current || map.current) return;
    map.current = L.map(box.current, { zoomControl: true }).setView([19.83, 85.85], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '© OpenStreetMap contributors · Flood extent © Copernicus EMS',
    }).addTo(map.current);
    layers.current = L.layerGroup().addTo(map.current);
    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);
        const [claims, flood, sum, fraud] = await Promise.all([
          getDashboard('claims.geojson'),
          getDashboard('flood-extent.geojson').catch(() => null),
          getDashboard('summary'),
          getDashboard('fraud-flags').catch(() => ({ items: [] })),
        ]);
        if (cancelled || !map.current || !layers.current) return;
        layers.current.clearLayers();
        if (flood?.features?.length) {
          L.geoJSON(flood, { style: { color: '#1F6FB2', weight: 1, fillOpacity: 0.25 } }).addTo(layers.current);
        }
        const points: L.LatLng[] = [];
        for (const f of claims.features || []) {
          const [lon, lat] = f.geometry.coordinates;
          const p = f.properties;
          const ll = L.latLng(lat, lon);
          points.push(ll);
          const flagText = (p.flags || []).map((x: string) => FLAG_TEXT[x] || x).join(', ');
          L.circleMarker(ll, {
            radius: 9,
            color: '#FFFFFF',
            weight: 2,
            fillColor: colour(p.damage_score),
            fillOpacity: 0.95,
          })
            .bindTooltip(
              `${p.claim_id} · damage ${p.damage_score}` +
                (p.satellite_damage_grade ? ` · satellite: ${p.satellite_damage_grade}` : '') +
                (flagText ? ` · ⚠ ${flagText}` : '')
            )
            .on('click', () => select.current(p.claim_id))
            .addTo(layers.current);
        }
        if (points.length) map.current.fitBounds(L.latLngBounds(points).pad(0.4), { maxZoom: 15 });
        setSummary(sum);
        setFlags(fraud.items || []);
      } catch (e) {
        if (!cancelled) setError(errorText(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <div>
      <div
        ref={box}
        style={{ width: '100%', height: '320px', borderRadius: '14px', border: '1.5px solid var(--border)', zIndex: 0 }}
        aria-label="Map of claims and the satellite flood extent"
      />
      {error && (
        <p role="alert" style={{ color: '#8A1C1C', fontWeight: 700, margin: '8px 0 0 0' }}>
          {error}
        </p>
      )}
      {summary && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px', fontSize: '0.85rem', fontWeight: 700 }}>
          <span className="badge">📸 {summary.photos} photos · {summary.claims} claims</span>
          <span className="badge">🔴 {summary.by_severity?.severe ?? 0} severe</span>
          <span className="badge">🛰️ {summary.satellite?.claims_inside_flood ?? 0} inside flood map</span>
          <span className="badge">⚠ {summary.claims_flagged} flagged</span>
        </div>
      )}
      {flags.length > 0 && (
        <div style={{ marginTop: '10px' }}>
          <strong style={{ fontSize: '0.95rem' }}>Needs a human check</strong>
          <ul style={{ margin: '6px 0 0 0', paddingLeft: '18px', fontSize: '0.88rem' }}>
            {flags.slice(0, 6).map((f, i) => (
              <li key={i}>
                <button
                  onClick={() => select.current(f.claim_id)}
                  style={{ background: 'none', border: 'none', padding: 0, color: 'var(--primary)', fontWeight: 700, cursor: 'pointer' }}
                >
                  {f.claim_id}
                </button>
                : {FLAG_TEXT[f.type] || f.type}
                {f.other_claim_id ? ` (${f.other_claim_id})` : ''} · {f.action}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p style={{ margin: '8px 0 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
        🔴 damage ≥ 70 · 🟡 40–69 · 🟢 below 40 · blue = satellite flood extent. Click a point to open the claim.
      </p>
    </div>
  );
};
