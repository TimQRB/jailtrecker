import { useEffect, useState } from "react";
import { api, type AuditEntry } from "../../api";

export default function AuditTab() {
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [action, setAction] = useState("");

  const load = () => {
    const q = action ? `?action=${encodeURIComponent(action)}&limit=300` : "?limit=300";
    api.audit.list(q).then(setItems).catch(() => {});
  };
  useEffect(() => {
    load();
  }, [action]);

  return (
    <div className="crud">
      <div className="row-form">
        <input placeholder="Фильтр по действию (login, create, delete…)" value={action} onChange={(e) => setAction(e.target.value)} />
      </div>
      <table>
        <thead>
          <tr>
            <th>Время</th>
            <th>Пользователь</th>
            <th>Действие</th>
            <th>Объект</th>
            <th>Детали</th>
            <th>IP</th>
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.id}>
              <td>{new Date(a.created_at).toLocaleString()}</td>
              <td>{a.user_email ?? "—"}</td>
              <td>{a.action}</td>
              <td>
                {a.entity_type ?? ""}
                {a.entity_id ? ` #${a.entity_id}` : ""}
              </td>
              <td>{a.detail ?? ""}</td>
              <td>{a.ip ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
