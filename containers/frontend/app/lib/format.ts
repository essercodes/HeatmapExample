export type DateInput = Date | string | number | null | undefined;

function toDate(value: DateInput): Date | null {
    if (value === null || value === undefined) return null;
    const date = value instanceof Date ? value : new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: DateInput): string {
    const date = toDate(value);
    if (!date) return "—";
    return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

const relativeUnits: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 365 * 24 * 60 * 60],
    ["month", 30 * 24 * 60 * 60],
    ["week", 7 * 24 * 60 * 60],
    ["day", 24 * 60 * 60],
    ["hour", 60 * 60],
    ["minute", 60],
];

export function formatRelative(value: DateInput, now = Date.now()): string {
    const date = toDate(value);
    if (!date) return "—";

    const seconds = (date.getTime() - now) / 1000;
    const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
    for (const [unit, unitSeconds] of relativeUnits) {
        if (Math.abs(seconds) >= unitSeconds) {
            return formatter.format(Math.round(seconds / unitSeconds), unit);
        }
    }
    return "just now";
}

export function toIsoString(value: DateInput): string | undefined {
    return toDate(value)?.toISOString();
}

// Good enough to tell sessions apart; not a full user agent parser.
export function describeUserAgent(userAgent: string | null | undefined): string {
    if (!userAgent) return "Unknown device";

    const browser =
        /Edg\//.test(userAgent) ? "Edge" :
        /OPR\/|Opera/.test(userAgent) ? "Opera" :
        /Firefox\//.test(userAgent) ? "Firefox" :
        /Chrome\/|CriOS\//.test(userAgent) ? "Chrome" :
        /Safari\//.test(userAgent) ? "Safari" :
        /curl\//.test(userAgent) ? "curl" :
        null;

    const os =
        /iPhone|iPad|iPod/.test(userAgent) ? "iOS" :
        /Android/.test(userAgent) ? "Android" :
        /Windows/.test(userAgent) ? "Windows" :
        /Mac OS X|Macintosh/.test(userAgent) ? "macOS" :
        /CrOS/.test(userAgent) ? "ChromeOS" :
        /Linux/.test(userAgent) ? "Linux" :
        null;

    if (browser && os) return `${browser} on ${os}`;
    return browser ?? os ?? "Unknown device";
}
