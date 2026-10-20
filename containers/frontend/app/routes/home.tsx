import type { Route } from "./+types/home";
import HeatMap from "../components/HeatMap";
import TimeSlider from "../components/TimeSlider";
import VehicleTypeFilter from "../components/VehicleTypeFilter";

import { useEffect, useEffectEvent, useRef, useState } from "react";
import { API_URL as API_URL_ENV } from "~/lib/api.server";

export function meta() {
    return [
        { title: "Heatmap" },
        { name: "description", content: "Union Cab Booking Heatmap" },
    ];
}

export const BUCKET_WIDTH_MIN = 15;
const BUCKET_WIDTH_MS = BUCKET_WIDTH_MIN * 60 * 1000;
const WINDOW_LENGTH_HOURS = 8;
const WINDOW_LENGTH_IN_MS = WINDOW_LENGTH_HOURS * 60 * 60 * 1000;
export const MAX_STEP = (WINDOW_LENGTH_HOURS * 60) / BUCKET_WIDTH_MIN - 1;


export interface TimeBucket {
    bucketStart: number;
    bucketEnd: number;
}

const DEFAULT_POLL_TIME_MIN = 5;

// Runs on the server (SSR), so the container's environment is visible here; the value
// reaches the browser through loaderData.
export async function loader() {
    const POLL_TIME_MIN = Number(process.env.POLL_TIME_MIN ?? DEFAULT_POLL_TIME_MIN);
    if (!Number.isFinite(POLL_TIME_MIN)) {
        throw new Error(`POLL_TIME_MIN must be a number, got "${process.env.POLL_TIME_MIN}"`);
    }
    const API_URL = API_URL_ENV ?? "NOT SET";

    return { POLL_TIME_MIN, API_URL };
}

const minutes_to_milliseconds = (m: number) => m * 60000;

export default function Home({ loaderData }: Route.ComponentProps) {
    const { POLL_TIME_MIN, API_URL } = loaderData;

    const defaultSliderValues: [number, number] = [0, 3];

    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    const [lastUpdated, setLastUpdated] = useState<number | null>();
    const [steps, setSteps] = useState<[number, number]>(defaultSliderValues);
    const [bucket, setBucket] = useState<TimeBucket | undefined>(undefined);
    const [hiddenVehicleTypes, setHiddenVehicleTypes] = useState<ReadonlySet<string>>(new Set());

    const toBucket = ([window_start, window_end]: [number, number]): TimeBucket => {
        const now = Date.now();
        const bucketStart = now + (window_start * BUCKET_WIDTH_MS);
        const bucketEnd = now + (window_end * BUCKET_WIDTH_MS);

        return {
            bucketStart: ((window_start === 0) ? bucketStart - WINDOW_LENGTH_IN_MS : bucketStart),
            bucketEnd: bucketEnd,
        }
    }

    const fetcherLoad = useEffectEvent(() => {
        const nextBucket = toBucket(steps);
        setBucket(nextBucket);
        setLastUpdated(Date.now());
        // fetcher.load(`/api/bookings?bucketStart=${nextBucket.bucketStart}&bucketEnd=${nextBucket.bucketEnd}`)
    });

    useEffect(() => {
        if (POLL_TIME_MIN <= 0) return;

        // Fetch now (login, slider change, tab visible again), then keep polling.
        fetcherLoad();

        const startPolling = () => {
            pollingRef.current = setInterval(() => {
                fetcherLoad();
            }, minutes_to_milliseconds(POLL_TIME_MIN))
        }
        startPolling();

        return () => {
            if (pollingRef.current === null) return;
            clearInterval(pollingRef.current);
        }
    }, [steps, POLL_TIME_MIN])

    const lastUpdatedString = (lastUpdated: number) => {
        const date = new Date(lastUpdated);
        return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`
    }

    // Error responses from /api/bookings don't carry bookings or vehicleTypes.
    /* const bookingsData = fetcher.data?.ok ? fetcher.data : undefined;
    const vehicleTypes = bookingsData?.vehicleTypes ?? [];
    const allBookings = bookingsData?.bookings;
    const bookings = useMemo(
        () => (allBookings ?? []).filter((booking) => !hiddenVehicleTypes.has(booking.vehicle_type)),
        [allBookings, hiddenVehicleTypes],
    ); */
    const vehicleTypes = ["R", "V", "S", "D", "ATS"];
    const bookings: { pickup_lng: number; pickup_lat: number; vehicle_type: string }[] = [];

    const toggleVehicleType = (vehicleType: string, shown: boolean) => {
        setHiddenVehicleTypes((prev) => {
            const next = new Set(prev);
            if (shown) next.delete(vehicleType);
            else next.add(vehicleType);
            return next;
        });
    }

    return (
        <div className="flex flex-col h-dvh typeset typeset-docs pb-11">
            <div className="flex grow justify-center">
                <div className="flex flex-col-reverse md:flex-col min-w-full justify-start gap-2">
                    <div className="type">{API_URL}</div>
                    <TimeSlider bucket={bucket} setSteps={setSteps} defaultValues={defaultSliderValues} />
                    <VehicleTypeFilter vehicleTypes={vehicleTypes} hiddenVehicleTypes={hiddenVehicleTypes} onToggle={toggleVehicleType} />

                    <div className="w-full grow">
                        <HeatMap bookings={bookings} fallback={<p >Loading map…</p>} />
                    </div>
                    <div className="self-start md:self-end italic text-xs mx-1">
                        Last Updated: {(!lastUpdated) ? "never" : lastUpdatedString(lastUpdated)}
                    </div>
                </div>
            </div>
        </div>
    );
}
