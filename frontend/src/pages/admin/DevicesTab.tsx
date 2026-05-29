import { useEffect, useState, type FormEvent } from "react";
import { api, type Device, type Inmate } from "../../api";

export default function DevicesTab() {
  const [items, setItems] = useState<Device[]>([]);
  const [inmates, setInmates] = useState<Inmate[]>([]);
  const [identifier, setIdentifier] = useState("");
  const [imei, setImei] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    api.devices.list().then(setItems).catch((e) => setError(e.message));
    api.inmates.list().then(setInmates).catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const nameById = new Map(inmates.map((i) => [i.id, i.full_name]));

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.devices.create({ identifier, imei });
      setIdentifier("");
      setImei("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const assign = async (id: number, inmateId: string) => {
    if (!inmateId) return;
    await api.devices.assign(id, Number(inmateId));
    load();
  };

  return (
    <div className="crud">
      <form className="row-form" onSubmit={create}>
        <input placeholder="Идентификатор" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
        <input placeholder="IMEI" value={imei} onChange={(e) => setImei(e.target.value)} required />
        <button type="submit">Добавить браслет</button>
      </form>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>IMEI</th>
            <th>Носитель</th>
            <th>Заряд</th>
            <th>Tamper</th>
            <th>Посл. связь</th>
            <th>Привязка</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((d) => (
            <tr key={d.id} className={d.tamper_state !== "ok" ? "sev-critical" : ""}>
              <td>{d.id}</td>
              <td>{d.imei}</td>
              <td>{d.inmate_id ? nameById.get(d.inmate_id) ?? d.inmate_id : "—"}</td>
              <td>{d.last_battery ?? "—"}%</td>
              <td>{d.tamper_state}</td>
              <td>{d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : "—"}</td>
              <td>
                <select defaultValue="" onChange={(e) => assign(d.id, e.target.value)}>
                  <option value="">— привязать —</option>
                  {inmates.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.full_name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <button onClick={() => api.devices.locateNow(d.id)}>Локация</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
