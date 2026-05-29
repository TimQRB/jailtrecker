// Типы DTO + обёртки fetch с JWT.

export type Role = "admin" | "warden" | "inspector";
export type SupervisionType = "house_arrest" | "facility" | "convoy";
export type CaseStatus = "active" | "suspended" | "closed";
export type ZoneType =
  | "home"
  | "work"
  | "allowed"
  | "forbidden"
  | "perimeter"
  | "route_corridor";
export type ScheduleRule = "must_be_inside" | "allowed_outside";
export type IncidentType =
  | "exit_zone"
  | "enter_forbidden"
  | "curfew_violation"
  | "route_deviation"
  | "tamper"
  | "low_battery"
  | "device_offline"
  | "sos";
export type Severity = "info" | "warning" | "critical";
export type TamperState = "ok" | "opened" | "strap_cut";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Inmate {
  id: number;
  full_name: string;
  inmate_number: string;
  date_of_birth: string | null;
  photo_url: string | null;
  supervisor_id: number | null;
  is_active: boolean;
  created_at: string;
}

export interface Case {
  id: number;
  inmate_id: number;
  case_number: string;
  article: string | null;
  supervision_type: SupervisionType;
  supervising_authority: string | null;
  status: CaseStatus;
  start_date: string | null;
  end_date: string | null;
  notes: string | null;
  created_at: string;
}

export interface Device {
  id: number;
  identifier: string;
  imei: string;
  dev_type: string;
  model_name: string | null;
  inmate_id: number | null;
  api_key: string;
  last_seen_at: string | null;
  last_battery: number | null;
  tamper_state: TamperState;
  is_active: boolean;
  created_at: string;
}

export interface Geofence {
  id: number;
  name: string;
  zone_type: ZoneType;
  coordinates: number[][]; // [[lon, lat], ...]
  inmate_id: number | null;
  case_id: number | null;
  is_active: boolean;
  created_at: string;
}

export interface Schedule {
  id: number;
  inmate_id: number;
  geofence_id: number;
  rule: ScheduleRule;
  day_of_week: number | null;
  start_time: string;
  end_time: string;
  is_active: boolean;
}

export interface LocationPoint {
  id: number;
  device_id: number;
  lat: number;
  lon: number;
  accuracy: number | null;
  speed: number | null;
  battery: number | null;
  source: string;
  recorded_at: string;
}

export interface Incident {
  id: number;
  inmate_id: number | null;
  device_id: number | null;
  incident_type: IncidentType;
  severity: Severity;
  geofence_id: number | null;
  message: string | null;
  lat: number | null;
  lon: number | null;
  acknowledged: boolean;
  acknowledged_by: number | null;
  acknowledged_at: string | null;
  created_at: string;
}

export interface AuditEntry {
  id: number;
  user_id: number | null;
  user_email: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  detail: string | null;
  ip: string | null;
  user_agent: string | null;
  created_at: string;
}

const TOKEN_KEY = "jailtracker_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = tokenStore.get();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    tokenStore.clear();
    window.location.href = "/login";
    throw new Error("Не авторизован");
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/auth/me"),

  inmates: {
    list: () => request<Inmate[]>("/api/inmates"),
    create: (b: Partial<Inmate>) =>
      request<Inmate>("/api/inmates", { method: "POST", body: JSON.stringify(b) }),
    update: (id: number, b: Partial<Inmate>) =>
      request<Inmate>(`/api/inmates/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
    remove: (id: number) => request<void>(`/api/inmates/${id}`, { method: "DELETE" }),
  },
  cases: {
    list: (inmateId?: number) =>
      request<Case[]>(`/api/cases${inmateId ? `?inmate_id=${inmateId}` : ""}`),
    create: (b: Partial<Case>) =>
      request<Case>("/api/cases", { method: "POST", body: JSON.stringify(b) }),
    update: (id: number, b: Partial<Case>) =>
      request<Case>(`/api/cases/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
    remove: (id: number) => request<void>(`/api/cases/${id}`, { method: "DELETE" }),
  },
  devices: {
    list: () => request<Device[]>("/api/devices"),
    create: (b: Partial<Device>) =>
      request<Device>("/api/devices", { method: "POST", body: JSON.stringify(b) }),
    update: (id: number, b: Partial<Device>) =>
      request<Device>(`/api/devices/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
    assign: (id: number, inmateId: number) =>
      request<Device>(`/api/devices/${id}/assign/${inmateId}`, { method: "POST" }),
    locateNow: (id: number) =>
      request<{ status: string }>(`/api/devices/${id}/locate-now`, { method: "POST" }),
    remove: (id: number) => request<void>(`/api/devices/${id}`, { method: "DELETE" }),
  },
  geofences: {
    list: () => request<Geofence[]>("/api/geofences"),
    create: (b: Partial<Geofence>) =>
      request<Geofence>("/api/geofences", { method: "POST", body: JSON.stringify(b) }),
    update: (id: number, b: Partial<Geofence>) =>
      request<Geofence>(`/api/geofences/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
    remove: (id: number) => request<void>(`/api/geofences/${id}`, { method: "DELETE" }),
  },
  schedules: {
    list: (inmateId?: number) =>
      request<Schedule[]>(`/api/schedules${inmateId ? `?inmate_id=${inmateId}` : ""}`),
    create: (b: Partial<Schedule>) =>
      request<Schedule>("/api/schedules", { method: "POST", body: JSON.stringify(b) }),
    remove: (id: number) => request<void>(`/api/schedules/${id}`, { method: "DELETE" }),
  },
  incidents: {
    list: (params = "") => request<Incident[]>(`/api/incidents${params}`),
    ack: (id: number) =>
      request<Incident>(`/api/incidents/${id}/ack`, { method: "POST" }),
  },
  audit: {
    list: (params = "") => request<AuditEntry[]>(`/api/audit${params}`),
  },
  track: (inmateId: number) =>
    request<LocationPoint[]>(`/api/inmates/${inmateId}/track`),
  lastLocation: (inmateId: number) =>
    request<LocationPoint | null>(`/api/inmates/${inmateId}/last-location`),

  users: {
    list: () => request<User[]>("/api/users"),
    create: (b: Partial<User> & { password: string }) =>
      request<User>("/api/users", { method: "POST", body: JSON.stringify(b) }),
    update: (id: number, b: Record<string, unknown>) =>
      request<User>(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
    remove: (id: number) => request<void>(`/api/users/${id}`, { method: "DELETE" }),
  },
};
