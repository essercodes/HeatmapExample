import { useRef } from "react";

import { Slider } from "./ui/slider";
import { MAX_STEP, type TimeBucket } from "~/routes/home";

export interface TimeSliderProps {
    bucket: TimeBucket | undefined;
    setSteps: (steps: [number, number]) => void;
    defaultValues: [number, number];
}

function formatTime(ms: number) {
    return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export default function TimeSlider(props: TimeSliderProps) {
    // Anchor "now" once on mount (client-side) so the slider's range doesn't
    // shift underfoot as time passes during the session.
    const timer = useRef<NodeJS.Timeout | undefined>(undefined);
    const DELAY = 500;
    const loading = props.bucket === undefined;

    /**
     * Debounce calls on bucket update.
     * @param step - currect slider step.
     * @returns lambda function to reset debounce 
     */
    const onSliderChange = (steps: number | readonly number[]) => {
        if (typeof steps === "number") {
            console.log("type of step should be number[]");
            return;
        }

        timer.current = setTimeout(() => {
            props.setSteps([steps[0], steps[1]])
        }, DELAY);

        return () => {
            clearTimeout(timer.current);
        }
    }

    return (
        <div className="flex flex-col my-2 gap-2">
            <div className="flex justify-center w-full mx-auto max-w-xs">
                {
                    loading ? <p>Loading...</p> :
                        <p>{formatTime(props.bucket?.bucketStart ?? 0) } ➔ {formatTime(props.bucket?.bucketEnd ?? 0)}</p>
                }
            </div>
            <div className="mx-2 flex gap-4 items-center justify-center">
                <div>Now</div>
                <div className="max-w-80 grow">
                    <Slider
                        defaultValue={props.defaultValues}
                        max={MAX_STEP}
                        step={1}
                        className="mx-auto w-full max-w-xs"
                        onValueChange={onSliderChange}
                    />
                </div>
                <div>Future</div>
            </div>
        </div>
    );
}
