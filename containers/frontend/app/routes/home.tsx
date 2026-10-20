import type { Route } from "./+types/home";
import HeatMap from "../components/HeatMap";
import type { HeatMapBooking } from "../components/HeatMapClient";
import TimeSlider from "../components/TimeSlider";
import VehicleTypeFilter from "../components/VehicleTypeFilter";

import { useEffect, useMemo, useRef, useState } from "react";
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
    // Only the latest request may set bookings, so a slow response can't overwrite a newer one.
    const requestIdRef = useRef(0);

    const [lastUpdated, setLastUpdated] = useState<number | null>();
    const [steps, setSteps] = useState<[number, number]>(defaultSliderValues);
    const [bucket, setBucket] = useState<TimeBucket | undefined>(undefined);
    const [hiddenVehicleTypes, setHiddenVehicleTypes] = useState<ReadonlySet<string>>(new Set());
    const [allBookings, setAllBookings] = useState<HeatMapBooking[]>([]);

    const toBucket = ([window_start, window_end]: [number, number]): TimeBucket => {
        const now = Date.now();
        const bucketStart = now + (window_start * BUCKET_WIDTH_MS);
        const bucketEnd = now + (window_end * BUCKET_WIDTH_MS);

        return {
            bucketStart: ((window_start === 0) ? bucketStart - WINDOW_LENGTH_IN_MS : bucketStart),
            bucketEnd: bucketEnd,
        }
    }

    const fetchBookings = async () => {
        const nextBucket = toBucket(steps);
        setBucket(nextBucket);
        const requestId = ++requestIdRef.current;

        try {
            const response = await fetch(
                `${API_URL}/booking/data/window?bucketStart=${nextBucket.bucketStart}&bucketEnd=${nextBucket.bucketEnd}`
            );
            if (requestId !== requestIdRef.current) return;

            if (response.status === 400 || response.status === 503) {
                const body: { error?: string } = await response.json().catch(() => ({}));
                alert(`Couldn't load bookings (${response.status}): ${body.error ?? response.statusText}`);
                return;
            }
            if (!response.ok) {
                console.error(`Couldn't load bookings: ${response.status} ${response.statusText}`);
                return;
            }

            const nextBookings: HeatMapBooking[] = await response.json();
            if (requestId !== requestIdRef.current) return;
            setAllBookings(nextBookings);
            setLastUpdated(Date.now());
        } catch (error) {
            console.error("Couldn't load bookings:", error);
        }
    };

    useEffect(() => {
        if (POLL_TIME_MIN <= 0) return;

        // Fetch now (login, slider change, tab visible again), then keep polling.
        void fetchBookings();

        const startPolling = () => {
            pollingRef.current = setInterval(() => {
                void fetchBookings();
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

    const vehicleTypes = ["R", "ATS", "D", "S", "V"]; // TODO: pull from /vehicles/...

    const bookings = useMemo(
        () => allBookings.filter((booking) => !hiddenVehicleTypes.has(booking.vehicle_type)),
        [allBookings, hiddenVehicleTypes],
    );

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
