import React from "react";
import HeroIcon from "@/components/icons/HeroIcon";
import type { SelectableHeroProps } from "@/types/domain";
import { UnstyledButton } from "@mantine/core";
import classes from "../../draft-predictor.module.css";

function SelectableHero({
    hero_id,
    hero_name,
    minHeight = 45,
    minWidth = 80,
    isPicked = false,
    canPick = true,
    handlePick,
}: SelectableHeroProps) {
    const disabled = !canPick || isPicked; // Disable if cannot pick or already picked

    const handleClick = () => {
        handlePick(hero_id);
    };

    return (
        <UnstyledButton
            onClick={handleClick}
            disabled={disabled}
            data-testid="hero-pick"
            className={[classes.heroBtn, isPicked && classes.heroPicked].filter(Boolean).join(" ")}
            style={{ cursor: disabled ? "default" : "pointer" }}
        >
            <HeroIcon
                key={hero_id}
                hero_id={hero_id}
                hero_name={hero_name}
                minHeight={minHeight}
                minWidth={minWidth}
            />
        </UnstyledButton>
    );
}

export default React.memo(SelectableHero);
