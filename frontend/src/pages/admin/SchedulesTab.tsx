import { useEffect, useState, type FormEvent } from "react";
import { api, type Geofence, type Inmate, type Schedule, type ScheduleRule } from "../../api";

const RULE_LABEL: Record<ScheduleRule, string> = {
  must_be_inside: "Обязан быть внутри (комендантский)",
  allowed_outside: "Разрешён выход",
};
const DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export default function SchedulesTab() {
  const [items, setItems] = useState<Schedule[]>([]);
  const [inmates, setInmates] = useState<Inmate[]>([]);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [inmateId, setInmateId] = useState<string>("");
  const [geofenceId, setGeofenceId] = useState<string>("");
  const [rule, setRule] = useState<ScheduleRule>("must_be_inside");
  const [day, setDay] = useState<string>("");
  const [start, setStart] = useState("22:00");
  const [end, setEnd] = useState("06:00");
  const [error, setError] = useState("");

  const load = () => {
    api.schedules.list().then(setItems).catch((e) => setError(e.message));
    api.inmates.list().then(setInmates).catch(() => {});
    api.geofences.list().then(setGeofences).catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!inmateId || !geofenceId) return;
    try {
      await api.schedules.create({
        inmate_id: Number(inmateId),
        geofence_id: Number(geofenceId),
        rule,
        day_of_week: day === "" ? null : Number(day),
        start_time: start,
        end_time: end,
      });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const remove = async (id: number) => {
    await api.schedules.remove(id);
    load();
  };

  return (
    <div className="crud">
      <form className="row-form" onSubmit={create}>
        <select value={inmateId} onChange={(e) => setInmateId(e.target.value)} required>
          <option value="">— поднадзорный —</option>
          {inmates.map((i) => (
            <option key={i.id} value={i.id}>
              {i.full_name}
            </option>
          ))}
        </select>
        <select value={geofenceId} onChange={(e) => setGeofenceId(e.target.value)} required>
          <option value="">— зона —</option>
          {geofences.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
        <select value={rule} onChange={(e) => setRule(e.target.value as ScheduleRule)}>
          {Object.entries(RULE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select value={day} onChange={(e) => setDay(e.target.value)}>
          <option value="">Ежедневно</option>
          {DAYS.map((d, i) => (
            <option key={i} value={i}>
              {d}
            </option>
          ))}
        </select>
        <input type="time" value={start} onChange={(e) => setStart(e.target.value)} />
        <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} />
        <button type="submit">Добавить</button>
      </form>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Поднадзорный</th>
            <th>Зона</th>
            <th>Правило</th>
            <th>День</th>
            <th>Время</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((s) => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td>{inmates.find((i) => i.id === s.inmate_id)?.full_name ?? s.inmate_id}</td>
              <td>{geofences.find((g) => g.id === s.geofence_id)?.name ?? s.geofence_id}</td>
              <td>{RULE_LABEL[s.rule]}</td>
              <td>{s.day_of_week === null ? "ежедн." : DAYS[s.day_of_week]}</td>
              <td>
                {s.start_time}–{s.end_time}
              </td>
              <td>
                <button className="danger" onClick={() => remove(s.id)}>
                  Удалить
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
