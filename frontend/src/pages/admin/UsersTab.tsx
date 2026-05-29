import { useEffect, useState, type FormEvent } from "react";
import { api, type Role, type User } from "../../api";

const ROLE_LABEL: Record<Role, string> = {
  admin: "Администрация ИУ",
  warden: "Надзиратель",
  inspector: "Инспектор УИИ",
};

export default function UsersTab() {
  const [items, setItems] = useState<User[]>([]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Role>("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const load = () => api.users.list().then(setItems).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.users.create({ email, full_name: fullName, role, password });
      setEmail("");
      setFullName("");
      setPassword("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить пользователя?")) return;
    try {
      await api.users.remove(id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  return (
    <div className="crud">
      <form className="row-form" onSubmit={create}>
        <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input placeholder="ФИО" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
        <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
          {Object.entries(ROLE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <input
          placeholder="Пароль"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">Создать</button>
      </form>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Email</th>
            <th>ФИО</th>
            <th>Роль</th>
            <th>Активен</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((u) => (
            <tr key={u.id}>
              <td>{u.id}</td>
              <td>{u.email}</td>
              <td>{u.full_name}</td>
              <td>{ROLE_LABEL[u.role]}</td>
              <td>{u.is_active ? "да" : "нет"}</td>
              <td>
                <button className="danger" onClick={() => remove(u.id)}>
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
