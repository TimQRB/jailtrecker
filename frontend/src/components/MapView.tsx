import { MapContainer, Marker, Popup, Polygon, Polyline } from "react-leaflet";
import L from "leaflet";
import BaseLayer, { ZONE_COLORS } from "./BaseLayer";
import type { Geofence, Inmate, LocationPoint } from "../api";

// фикс дефолтных иконок Leaflet под Vite
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

export interface LivePosition {
  inmate_id: number | null;
  lat: number;
  lon: number;
  battery?: number | null;
}

interface Props {
  geofences: Geofence[];
  positions: Record<number, LivePosition>;
  inmates: Inmate[];
  track?: LocationPoint[];
  center?: [number, number];
}

export default function MapView({ geofences, positions, inmates, track, center }: Props) {
  const start: [number, number] = center ?? [51.1605, 71.4704]; // Астана по умолчанию
  const nameById = new Map(inmates.map((i) => [i.id, i.full_name]));

  return (
    <MapContainer center={start} zoom={12} style={{ height: "100%", width: "100%" }}>
      <BaseLayer />

      {geofences.map((g) => (
        <Polygon
          key={g.id}
          positions={g.coordinates.map(([lon, lat]) => [lat, lon] as [number, number])}
          pathOptions={{ color: ZONE_COLORS[g.zone_type] ?? "#555", fillOpacity: 0.15 }}
        >
          <Popup>
            {g.name} ({g.zone_type})
          </Popup>
        </Polygon>
      ))}

      {track && track.length > 1 && (
        <Polyline
          positions={track.map((p) => [p.lat, p.lon] as [number, number])}
          pathOptions={{ color: "#1976d2" }}
        />
      )}

      {Object.entries(positions).map(([inmateId, pos]) => (
        <Marker key={inmateId} position={[pos.lat, pos.lon]} icon={icon}>
          <Popup>
            <b>{nameById.get(Number(inmateId)) ?? `ID ${inmateId}`}</b>
            <br />
            Заряд: {pos.battery ?? "—"}%
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
