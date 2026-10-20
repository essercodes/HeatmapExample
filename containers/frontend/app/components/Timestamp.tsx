import { formatDateTime, formatRelative, toIsoString, type DateInput } from "../lib/format";

export interface TimestampProps {
    value: DateInput;
    relative?: boolean;
    className?: string;
}

// Server and browser time zones differ, so the rendered text is allowed to
// change during hydration.
export function Timestamp({ value, relative = false, className }: TimestampProps) {
    const iso = toIsoString(value);
    if (!iso) return <span className={className}>—</span>;

    return (
        <time
            dateTime={iso}
            title={formatDateTime(value)}
            className={className}
            suppressHydrationWarning
        >
            {relative ? formatRelative(value) : formatDateTime(value)}
        </time>
    );
}
