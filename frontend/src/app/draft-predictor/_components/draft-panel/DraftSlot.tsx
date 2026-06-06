import HeroIcon from "@/components/icons/HeroIcon";
import type { DraftSlotProps } from "@/types/domain";
import { UnstyledButton } from "@mantine/core";
import classes from "../../draft-predictor.module.css";

/**
 * A draft slot for selecting a hero (desktop view).
 * Neo-brutalist box: neutral border, pulsing cyan border when active,
 * ghost index number when empty.
 */
export default function DraftSlot({
    heroId,
    onClick,
    isActive,
    index,
}: DraftSlotProps) {
    return (
        <UnstyledButton
            onClick={onClick}
            className={[classes.slot, heroId != null && classes.slotFilled, isActive && classes.slotActive].filter(Boolean).join(" ")}
        >
            {heroId != null ? (
                <HeroIcon hero_id={heroId} hero_name="hero_name_placeholder" />
            ) : (
                <span className={classes.slotIndex}>{(index ?? 0) + 1}</span>
            )}
        </UnstyledButton>
    );
}
