import { Checkbox } from "./ui/checkbox";
import { Label } from "./ui/label";

export interface VehicleTypeFilterProps {
    vehicleTypes: string[];
    hiddenVehicleTypes: ReadonlySet<string>;
    onToggle: (vehicleType: string, shown: boolean) => void;
}

export default function VehicleTypeFilter(props: VehicleTypeFilterProps) {
    if (props.vehicleTypes.length === 0) return null;

    return (
        <div className="mx-2 flex flex-wrap gap-4 items-center justify-center">
            <div>Vehicle type:</div>
            {props.vehicleTypes.map((vehicleType) => (
                <Label key={vehicleType}>
                    <Checkbox
                        checked={!props.hiddenVehicleTypes.has(vehicleType)}
                        onCheckedChange={(checked) => props.onToggle(vehicleType, checked)}
                    />
                    {vehicleType}
                </Label>
            ))}
        </div>
    );
}
