import {
  lazy,
  Suspense,
  useEffect,
  useState,
  type PropsWithChildren,
  type ReactNode,
} from "react";

import type { HeatMapClientProps, HeatMapBooking } from "./HeatMapClient";

export type { HeatMapBooking };

const LazyHeatMapClient = lazy(() => import("./HeatMapClient"));

function ClientOnly({
  children,
  fallback,
}: PropsWithChildren<{ fallback?: ReactNode }>) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  return mounted ? children : (fallback ?? null);
}

export interface HeatMapProps extends HeatMapClientProps {
  fallback?: ReactNode;
}

export default function HeatMap({ fallback, ...props }: HeatMapProps) {
  return (
    <ClientOnly fallback={fallback}>
      <Suspense fallback={fallback}>
        <LazyHeatMapClient {...props} />
      </Suspense>
    </ClientOnly>
  );
}
