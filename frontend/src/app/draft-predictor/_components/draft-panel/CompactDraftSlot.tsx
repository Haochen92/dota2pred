import type { DraftSlotProps } from "@/types/domain";
import HeroAvatar from "@/components/icons/HeroAvatar";
import { UnstyledButton } from "@mantine/core";
import classes from "../../draft-predictor.module.css";

/**
 * Compact draft slot shown in mobile view.
 * Mirrors DraftSlot but uses the smaller HeroAvatar icon.
 */
export default function CompactDraftSlot({
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
                <HeroAvatar hero_id={heroId} hero_name="hero_name_placeholder" />
            ) : (
                <span className={classes.slotIndex}>{(index ?? 0) + 1}</span>
            )}
        </UnstyledButton>
    );
}
