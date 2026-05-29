import { useEffect, useState } from "react";
import { api, type Geofence, type Incident, type Inmate } from "../api";
import { useLiveBus } from "../useLiveBus";
import MapView, { type LivePosition } from "../components/MapView";

const SEV_LABEL: Record<string, string> = {
  info: "инфо",
  warning: "внимание",
  critical: "КРИТ",
};

export default function Dashboard() {
  const [inmates, setInmates] = useState<Inmate[]>([]);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [positions, setPositions] = useState<Record<number, LivePosition>>({});

  useEffect(() => {
    api.inmates.list().then(setInmates).catch(() => {});
    api.geofences.list().then(setGeofences).catch(() => {});
    api.incidents.list("?limit=50").then(setIncidents).catch(() => {});
    // подтянуть последние позиции
    api.inmates.list().then(async (list) => {
      for (const inm of list) {
        const loc = await api.lastLocation(inm.id).catch(() => null);
        if (loc) {
          setPositions((p) => ({
            ...p,
            [inm.id]: { inmate_id: inm.id, lat: loc.lat, lon: loc.lon, battery: loc.battery },
          }));
        }
      }
    });
  }, []);

  const { connected } = useLiveBus((m) => {
    if (m.type === "location" && m.payload) {
      const p = m.payload as Record<string, number | null>;
      const id = p.inmate_id as number | null;
      if (id != null) {
        setPositions((prev) => ({
          ...prev,
          [id]: {
            inmate_id: id,
            lat: p.lat as number,
            lon: p.lon as number,
            battery: p.battery,
          },
        }));
      }
    } else if (m.type === "incident") {
      setIncidents((prev) => [m.payload as unknown as Incident, ...prev].slice(0, 100));
    }
  });

  const nameById = new Map(inmates.map((i) => [i.id, i.full_name]));

  return (
    <div className="dashboard">
      <div className="map-pane">
        <MapView geofences={geofences} positions={positions} inmates={inmates} />
      </div>
      <aside className="side-pane">
        <div className="side-section">
          <h3>
            Подключение{" "}
            <span className={connected ? "dot ok" : "dot off"} title={connected ? "online" : "offline"} />
          </h3>
          <h3>Поднадзорные ({inmates.length})</h3>
          <ul className="list">
            {inmates.map((i) => (
              <li key={i.id}>
                <b>{i.full_name}</b>
                <span className="muted"> №{i.inmate_number}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="side-section">
          <h3>Инциденты</h3>
          <ul className="list">
            {incidents.map((inc) => (
              <li key={inc.id} className={`incident sev-${inc.severity}`}>
                <span className="badge">{SEV_LABEL[inc.severity]}</span>{" "}
                {inc.message || inc.incident_type}
                <div className="muted">
                  {inc.inmate_id ? nameById.get(inc.inmate_id) ?? `ID ${inc.inmate_id}` : "—"} ·{" "}
                  {new Date(inc.created_at).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}
