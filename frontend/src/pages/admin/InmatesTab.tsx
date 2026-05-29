import { useEffect, useState, type FormEvent } from "react";
import { api, type Inmate } from "../../api";

export default function InmatesTab() {
  const [items, setItems] = useState<Inmate[]>([]);
  const [fullName, setFullName] = useState("");
  const [number, setNumber] = useState("");
  const [dob, setDob] = useState("");
  const [error, setError] = useState("");

  const load = () => api.inmates.list().then(setItems).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.inmates.create({
        full_name: fullName,
        inmate_number: number,
        date_of_birth: dob || null,
      });
      setFullName("");
      setNumber("");
      setDob("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить поднадзорного?")) return;
    await api.inmates.remove(id);
    load();
  };

  return (
    <div className="crud">
      <form className="row-form" onSubmit={create}>
        <input placeholder="ФИО" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        <input placeholder="Личный номер" value={number} onChange={(e) => setNumber(e.target.value)} required />
        <input type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
        <button type="submit">Добавить</button>
      </form>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>ФИО</th>
            <th>Номер</th>
            <th>Дата рожд.</th>
            <th>Активен</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((i) => (
            <tr key={i.id}>
              <td>{i.id}</td>
              <td>{i.full_name}</td>
              <td>{i.inmate_number}</td>
              <td>{i.date_of_birth ?? "—"}</td>
              <td>{i.is_active ? "да" : "нет"}</td>
              <td>
                <button className="danger" onClick={() => remove(i.id)}>
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
