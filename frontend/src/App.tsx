import { Navigate, Route, Routes, Link, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Admin from "./pages/admin/Admin";

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center">Загрузка…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Shell({ children }: { children: JSX.Element }) {
  const { user, logout } = useAuth();
  const loc = useLocation();
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">jailtracker</span>
        <nav>
          <Link className={loc.pathname === "/" ? "active" : ""} to="/">
            Карта
          </Link>
          <Link className={loc.pathname.startsWith("/admin") ? "active" : ""} to="/admin">
            Администрирование
          </Link>
        </nav>
        <span className="spacer" />
        <span className="user">{user?.full_name}</span>
        <button onClick={logout}>Выход</button>
      </header>
      <main>{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Shell>
              <Dashboard />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/admin"
        element={
          <Protected>
            <Shell>
              <Admin />
            </Shell>
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
