import { useEffect, useRef } from "react";
import { MapContainer, useMap } from "react-leaflet";
import L from "leaflet";
import "@geoman-io/leaflet-geoman-free";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";
import BaseLayer, { ZONE_COLORS } from "./BaseLayer";
import type { Geofence } from "../api";

// кольцо координат в формате API: [[lon, lat], ...]
type Ring = number[][];

function ringFromLayer(layer: L.Polygon): Ring {
  const latlngs = layer.getLatLngs()[0] as L.LatLng[];
  return latlngs.map((p) => [p.lng, p.lat]);
}

interface GeomanProps {
  geofences: Geofence[];
  onCreate: (coords: Ring) => void;
  onUpdate: (id: number, coords: Ring) => void;
  onDelete: (id: number) => void;
}

function GeomanController({ geofences, onCreate, onUpdate, onDelete }: GeomanProps) {
  const map = useMap();
  // храним свежие колбэки в ref, чтобы не переинициализировать geoman на каждый рендер
  const cbs = useRef({ onCreate, onUpdate, onDelete });
  cbs.current = { onCreate, onUpdate, onDelete };

  // тулбар рисования — инициализируем один раз
  useEffect(() => {
    map.pm.addControls({
      position: "topleft",
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawCircle: false,
      drawText: false,
      drawRectangle: true,
      drawPolygon: true,
      editMode: true,
      dragMode: true,
      cutPolygon: false,
      removalMode: true,
      rotateMode: false,
    });
    try {
      map.pm.setLang("ru");
    } catch {
      /* язык не критичен */
    }

    const handleCreate = (e: { layer: L.Layer } & Record<string, unknown>) => {
      const layer = e.layer as L.Polygon;
      const coords = ringFromLayer(layer);
      // временный слой убираем — после сохранения список перерисуется из БД
      map.removeLayer(layer);
      cbs.current.onCreate(coords);
    };
    map.on("pm:create", handleCreate);

    return () => {
      map.off("pm:create", handleCreate);
      map.pm.removeControls();
    };
  }, [map]);

  // существующие геозоны — перерисовываем при изменении списка
  useEffect(() => {
    const group = L.featureGroup().addTo(map);
    geofences.forEach((g) => {
      if (!g.coordinates?.length) return;
      const latlngs = g.coordinates.map(([lon, lat]) => [lat, lon]) as [number, number][];
      const poly = L.polygon(latlngs, {
        color: ZONE_COLORS[g.zone_type] ?? "#555",
        fillOpacity: 0.15,
      });
      poly.bindTooltip(`${g.name} (${g.zone_type})`);
      poly.addTo(group);
      poly.on("pm:update", () => cbs.current.onUpdate(g.id, ringFromLayer(poly)));
      poly.on("pm:remove", () => cbs.current.onDelete(g.id));
    });
    return () => {
      group.remove();
    };
  }, [map, geofences]);

  return null;
}

export default function GeofenceEditor(props: GeomanProps & { center?: [number, number] }) {
  const start: [number, number] = props.center ?? [51.1605, 71.4704];
  return (
    <MapContainer center={start} zoom={12} style={{ height: 480, width: "100%" }}>
      <BaseLayer />
      <GeomanController {...props} />
    </MapContainer>
  );
}
