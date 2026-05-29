import { useEffect, useState } from "react";
import { api, type Incident, type Inmate } from "../../api";

const SEV_LABEL: Record<string, string> = {
  info: "инфо",
  warning: "внимание",
  critical: "КРИТ",
};

export default function IncidentsTab() {
  const [items, setItems] = useState<Incident[]>([]);
  const [inmates, setInmates] = useState<Inmate[]>([]);
  const [onlyOpen, setOnlyOpen] = useState(true);

  const load = () => {
    const q = onlyOpen ? "?acknowledged=false&limit=200" : "?limit=200";
    api.incidents.list(q).then(setItems).catch(() => {});
  };
  useEffect(() => {
    api.inmates.list().then(setInmates).catch(() => {});
  }, []);
  useEffect(() => {
    load();
  }, [onlyOpen]);

  const nameById = new Map(inmates.map((i) => [i.id, i.full_name]));

  const ack = async (id: number) => {
    await api.incidents.ack(id);
    load();
  };

  return (
    <div className="crud">
      <label className="row-form">
        <input type="checkbox" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} />
        Только неквитированные
      </label>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Уровень</th>
            <th>Тип</th>
            <th>Поднадзорный</th>
            <th>Сообщение</th>
            <th>Время</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((inc) => (
            <tr key={inc.id} className={`sev-${inc.severity}`}>
              <td>{inc.id}</td>
              <td>
                <span className="badge">{SEV_LABEL[inc.severity]}</span>
              </td>
              <td>{inc.incident_type}</td>
              <td>{inc.inmate_id ? nameById.get(inc.inmate_id) ?? inc.inmate_id : "—"}</td>
              <td>{inc.message}</td>
              <td>{new Date(inc.created_at).toLocaleString()}</td>
              <td>
                {inc.acknowledged ? (
                  <span className="muted">квитировано</span>
                ) : (
                  <button onClick={() => ack(inc.id)}>Квитировать</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
