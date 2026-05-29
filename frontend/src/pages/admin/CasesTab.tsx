import { useEffect, useState, type FormEvent } from "react";
import { api, type Case, type Inmate, type SupervisionType } from "../../api";

const SUP_LABEL: Record<SupervisionType, string> = {
  house_arrest: "Домашний арест",
  facility: "Внутри ИУ",
  convoy: "Конвоирование",
};

export default function CasesTab() {
  const [items, setItems] = useState<Case[]>([]);
  const [inmates, setInmates] = useState<Inmate[]>([]);
  const [inmateId, setInmateId] = useState<number | "">("");
  const [caseNumber, setCaseNumber] = useState("");
  const [article, setArticle] = useState("");
  const [supervision, setSupervision] = useState<SupervisionType>("house_arrest");
  const [error, setError] = useState("");

  const load = () => {
    api.cases.list().then(setItems).catch((e) => setError(e.message));
    api.inmates.list().then(setInmates).catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const nameById = new Map(inmates.map((i) => [i.id, i.full_name]));

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (inmateId === "") return;
    try {
      await api.cases.create({
        inmate_id: Number(inmateId),
        case_number: caseNumber,
        article: article || null,
        supervision_type: supervision,
      });
      setCaseNumber("");
      setArticle("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить дело?")) return;
    await api.cases.remove(id);
    load();
  };

  return (
    <div className="crud">
      <form className="row-form" onSubmit={create}>
        <select value={inmateId} onChange={(e) => setInmateId(Number(e.target.value))} required>
          <option value="">— поднадзорный —</option>
          {inmates.map((i) => (
            <option key={i.id} value={i.id}>
              {i.full_name}
            </option>
          ))}
        </select>
        <input placeholder="Номер дела" value={caseNumber} onChange={(e) => setCaseNumber(e.target.value)} required />
        <input placeholder="Статья" value={article} onChange={(e) => setArticle(e.target.value)} />
        <select value={supervision} onChange={(e) => setSupervision(e.target.value as SupervisionType)}>
          {Object.entries(SUP_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <button type="submit">Добавить</button>
      </form>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Дело</th>
            <th>Поднадзорный</th>
            <th>Статья</th>
            <th>Тип надзора</th>
            <th>Статус</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id}>
              <td>{c.id}</td>
              <td>{c.case_number}</td>
              <td>{nameById.get(c.inmate_id) ?? c.inmate_id}</td>
              <td>{c.article ?? "—"}</td>
              <td>{SUP_LABEL[c.supervision_type]}</td>
              <td>{c.status}</td>
              <td>
                <button className="danger" onClick={() => remove(c.id)}>
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
