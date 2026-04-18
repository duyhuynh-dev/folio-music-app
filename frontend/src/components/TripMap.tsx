"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

export interface Moment {
  id: string;
  photoUrl: string;
  trackName: string;
  trackArtist: string;
  trackReason: string;
  trackPreviewUrl: string | null;
  latitude: number;
  longitude: number;
  takenAt: string | null;
}

interface TripMapProps {
  moments: Moment[];
  accessToken: string;
  onMomentClick?: (moment: Moment) => void;
}

export default function TripMap({
  moments,
  accessToken,
  onMomentClick,
}: TripMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const [selectedMoment, setSelectedMoment] = useState<Moment | null>(null);

  useEffect(() => {
    if (!containerRef.current || moments.length === 0) return;

    mapboxgl.accessToken = accessToken;

    const bounds = new mapboxgl.LngLatBounds();
    moments.forEach((m) => bounds.extend([m.longitude, m.latitude]));

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      bounds,
      fitBoundsOptions: { padding: 60 },
    });

    mapRef.current = map;

    map.on("load", () => {
      // Route line between moments
      if (moments.length > 1) {
        map.addSource("route", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: {
              type: "LineString",
              coordinates: moments.map((m) => [m.longitude, m.latitude]),
            },
          },
        });

        map.addLayer({
          id: "route-line",
          type: "line",
          source: "route",
          layout: { "line-join": "round", "line-cap": "round" },
          paint: {
            "line-color": "#3b82f6",
            "line-width": 2,
            "line-opacity": 0.6,
          },
        });
      }

      // Markers for each moment
      moments.forEach((moment, index) => {
        const el = document.createElement("div");
        el.className = "folio-marker";
        el.style.cssText = `
          width: 32px; height: 32px; border-radius: 50%;
          background: #3b82f6; color: white; display: flex;
          align-items: center; justify-content: center;
          font-size: 13px; font-weight: 600; cursor: pointer;
          border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.25);
        `;
        el.textContent = String(index + 1);

        const popup = new mapboxgl.Popup({
          offset: 20,
          closeButton: true,
          maxWidth: "260px",
        }).setHTML(`
          <div style="font-family: system-ui, sans-serif;">
            <img src="${moment.photoUrl}" alt="" style="width:100%; border-radius:6px; margin-bottom:8px;" />
            <p style="margin:0; font-weight:600; font-size:13px;">${moment.trackName}</p>
            <p style="margin:2px 0 0; font-size:12px; color:#666;">${moment.trackArtist}</p>
            <p style="margin:6px 0 0; font-size:11px; color:#888; font-style:italic;">${moment.trackReason}</p>
          </div>
        `);

        el.addEventListener("click", () => {
          setSelectedMoment(moment);
          onMomentClick?.(moment);
        });

        new mapboxgl.Marker(el)
          .setLngLat([moment.longitude, moment.latitude])
          .setPopup(popup)
          .addTo(map);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [moments, accessToken, onMomentClick]);

  return (
    <div className="relative w-full h-full min-h-[400px] rounded-xl overflow-hidden">
      <div ref={containerRef} className="absolute inset-0" />
      {moments.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-zinc-400 text-sm">
          No moments with location data yet
        </div>
      )}
    </div>
  );
}
