import { useState } from "react";
import InmatesTab from "./InmatesTab";
import CasesTab from "./CasesTab";
import DevicesTab from "./DevicesTab";
import GeofencesTab from "./GeofencesTab";
import SchedulesTab from "./SchedulesTab";
import IncidentsTab from "./IncidentsTab";
import UsersTab from "./UsersTab";
import AuditTab from "./AuditTab";

const TABS = [
  { key: "inmates", label: "Поднадзорные", el: <InmatesTab /> },
  { key: "cases", label: "Дела", el: <CasesTab /> },
  { key: "devices", label: "Браслеты", el: <DevicesTab /> },
  { key: "geofences", label: "Геозоны", el: <GeofencesTab /> },
  { key: "schedules", label: "Расписания", el: <SchedulesTab /> },
  { key: "incidents", label: "Инциденты", el: <IncidentsTab /> },
  { key: "users", label: "Пользователи", el: <UsersTab /> },
  { key: "audit", label: "Аудит", el: <AuditTab /> },
] as const;

export default function Admin() {
  const [active, setActive] = useState<string>("inmates");
  const current = TABS.find((t) => t.key === active) ?? TABS[0];

  return (
    <div className="admin">
      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={t.key === active ? "tab active" : "tab"}
            onClick={() => setActive(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="tab-body">{current.el}</div>
    </div>
  );
}
