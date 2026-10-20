import { useEffect, useState } from "react";
import { Feature } from "ol";
import Point from "ol/geom/Point";
import Heatmap from "ol/layer/Heatmap";
import { fromLonLat } from "ol/proj";
import VectorSource from "ol/source/Vector";
import "ol/ol.css";

import { Map, TargetDiv, View } from "@essercodes/r-ol";
import { useMap } from "@essercodes/r-ol/context";
import { TileLayer } from "@essercodes/r-ol/layer";
import { ImageTileSource } from "@essercodes/r-ol/source";

export type HeatMapBooking = { pickup_lng: number; pickup_lat: number; vehicle_type: string };

export interface HeatMapClientProps {
  bookings: HeatMapBooking[];
}

// Center of the contiguous US, in map (EPSG:3857) coordinates.
const DEFAULT_CENTER = fromLonLat([-89.3844334, 43.0747746]);

function HeatmapBookingsLayer({ bookings }: { bookings: HeatMapBooking[] }) {
  const map = useMap();
  const [source] = useState(() => new VectorSource());
  const [layer] = useState(() => new Heatmap({ source, blur: 20, radius: 14 }));

  // r-ol has no built-in heatmap component, so the layer is added directly
  // to the underlying OpenLayers map instance via useMap().
  useEffect(() => {
    map.addLayer(layer);
    return () => {
      map.removeLayer(layer);
    };
  }, [map, layer]);

  useEffect(() => {
    source.clear();
    source.addFeatures(
      bookings.map(
        (point) => new Feature(new Point(fromLonLat([point.pickup_lng, point.pickup_lat]))),
      ),
    );
  }, [bookings, source]);

  return null;
}

export default function HeatMapClient({ bookings }: HeatMapClientProps) {
  return (
    <Map>
      <TargetDiv style={{ height: "100%", width: "100%" }} />
      <View zoom={10} center={DEFAULT_CENTER} />
      <TileLayer>
        <ImageTileSource
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attributions="Map data from OpenStreetMap"
        />
      </TileLayer>
      <HeatmapBookingsLayer bookings={bookings} />
    </Map>
  );
}
