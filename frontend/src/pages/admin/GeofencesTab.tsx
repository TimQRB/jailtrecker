import { useEffect, useRef, useState } from "react";
import { api, type Geofence, type Inmate, type ZoneType } from "../../api";
import GeofenceEditor from "../../components/GeofenceEditor";

const ZONE_LABEL: Record<ZoneType, string> = {
  home: "Дом (обязан внутри)",
  work: "Работа/учёба",
  allowed: "Разрешённая",
  forbidden: "Запретная",
  perimeter: "Периметр ИУ",
  route_corridor: "Коридор маршрута",
};

export default function GeofencesTab() {
  const [items, setItems] = useState<Geofence[]>([]);
  const [inmates, setInmates] = useState<Inmate[]>([]);
  const [name, setName] = useState("");
  const [zoneType, setZoneType] = useState<ZoneType>("home");
  const [inmateId, setInmateId] = useState<string>("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  // метаданные для следующей нарисованной зоны — в ref, чтобы колбэк карты видел свежие значения
  const metaRef = useRef({ name, zoneType, inmateId });
  metaRef.current = { name, zoneType, inmateId };

  const load = () => {
    api.geofences.list().then(setItems).catch((e) => setError(e.message));
    api.inmates.list().then(setInmates).catch(() => {});
  };
  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (coordinates: number[][]) => {
    setError("");
    const { name: n, zoneType: zt, inmateId: iid } = metaRef.current;
    if (!n.trim()) {
      setError("Сначала укажите название зоны, потом рисуйте полигон");
      load(); // перерисовать карту (временный слой уже удалён)
      return;
    }
    try {
      await api.geofences.create({
        name: n,
        zone_type: zt,
        coordinates,
        inmate_id: iid ? Number(iid) : null,
      });
      setName("");
      setInfo(`Зона «${n}» сохранена`);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
      load();
    }
  };

  const handleUpdate = async (id: number, coordinates: number[][]) => {
    try {
      await api.geofences.update(id, { coordinates });
      setInfo("Геометрия зоны обновлена");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
      load();
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.geofences.remove(id);
      setInfo("Зона удалена");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
      load();
    }
  };

  const removeFromTable = async (id: number) => {
    if (!confirm("Удалить геозону?")) return;
    await handleDelete(id);
  };

  return (
    <div className="crud">
      <div className="row-form">
        <input placeholder="Название зоны" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={zoneType} onChange={(e) => setZoneType(e.target.value as ZoneType)}>
          {Object.entries(ZONE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select value={inmateId} onChange={(e) => setInmateId(e.target.value)}>
          <option value="">Общая (все)</option>
          {inmates.map((i) => (
            <option key={i.id} value={i.id}>
              {i.full_name}
            </option>
          ))}
        </select>
      </div>
      <p className="muted">
        Укажите название и тип зоны, затем нарисуйте полигон инструментом на карте (слева вверху).
        Вершины существующих зон можно править и перетаскивать; удаление — режимом «корзина».
      </p>
      {error && <div className="error">{error}</div>}
      {info && <div className="muted">{info}</div>}

      <GeofenceEditor
        geofences={items}
        onCreate={handleCreate}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
      />

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Тип</th>
            <th>Привязка</th>
            <th>Точек</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((g) => (
            <tr key={g.id}>
              <td>{g.id}</td>
              <td>{g.name}</td>
              <td>{ZONE_LABEL[g.zone_type]}</td>
              <td>{g.inmate_id ?? "общая"}</td>
              <td>{g.coordinates.length}</td>
              <td>
                <button className="danger" onClick={() => removeFromTable(g.id)}>
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
