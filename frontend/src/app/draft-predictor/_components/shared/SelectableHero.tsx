import HeroIcon from "@/components/icons/HeroIcon";
import type { SelectableHeroProps } from "@/types/domain";
import { UnstyledButton } from "@mantine/core";


export default function SelectableHero({
    hero_id,
    hero_name,
    minHeight=45,
    minWidth=80,
    isPicked=false,
    canPick=true,
    handlePick,
}: SelectableHeroProps) {

    const disabled = !canPick || isPicked; // Disable if cannot pick or already picked

    const handleClick = () => {
         handlePick(hero_id);
    }

    return (
        <UnstyledButton
            onClick={handleClick}
            disabled={disabled}
            style={{
                opacity: isPicked ? 0.2 : 1,
                cursor: disabled ? 'default' : 'pointer',
                transition: 'opacity 0.2s ease'
            }}
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
