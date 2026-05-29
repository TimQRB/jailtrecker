import { useEffect } from "react";
import { TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// мост: расширяет L методом L.maplibreGL; плагин ожидает глобальный maplibregl
(window as unknown as { maplibregl: typeof maplibregl }).maplibregl = maplibregl;
import "@maplibre/maplibre-gl-leaflet";

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY as string | undefined;
export const MAPTILER_STYLE = MAPTILER_KEY
  ? `https://api.maptiler.com/maps/streets-v4/style.json?key=${MAPTILER_KEY}`
  : undefined;

/**
 * Подложка карты: векторный стиль MapTiler (MapLibre GL) под Leaflet-оверлеями.
 * Без ключа — растровый OpenStreetMap-фолбэк.
 */
export default function BaseLayer() {
  const map = useMap();
  useEffect(() => {
    if (!MAPTILER_STYLE) return;
    // @ts-expect-error — метод добавляется плагином maplibre-gl-leaflet
    const gl = L.maplibreGL({ style: MAPTILER_STYLE, attribution: "&copy; MapTiler &copy; OpenStreetMap" });
    gl.addTo(map);
    return () => {
      map.removeLayer(gl);
    };
  }, [map]);

  if (MAPTILER_STYLE) return null;
  return (
    <TileLayer
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      attribution="&copy; OpenStreetMap"
    />
  );
}

export const ZONE_COLORS: Record<string, string> = {
  home: "#2e7d32",
  work: "#1565c0",
  allowed: "#00838f",
  forbidden: "#c62828",
  perimeter: "#6a1b9a",
  route_corridor: "#ef6c00",
};
