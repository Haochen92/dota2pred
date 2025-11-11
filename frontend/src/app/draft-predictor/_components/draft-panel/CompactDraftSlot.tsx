import type { DraftSlotProps } from "@/types/domain";
import HeroAvatar from "@/components/icons/HeroAvatar";
import { UnstyledButton} from "@mantine/core";


export default function CompactDraftSlot({
    heroId,
    onClick,
    isActive,
}: DraftSlotProps) {
    return (
        <UnstyledButton
            onClick={onClick}
            style={ (theme) => ({
                display: 'flex',
                flexGrow: 1,
                aspectRatio: '42.4/30',
                borderRadius: '4px',
                boxShadow: isActive ? `inset 0 0 0 2px ${theme.colors.blue[4]}` : 'none',
                transition: 'box-shadow 0.2s ease',
                backgroundColor: heroId ? 'transparent' : theme.colors.gray[9],
            })}
        >{ heroId && <HeroAvatar
            hero_id={heroId}
            hero_name='hero_name_placeholder'
            />
        }
        </UnstyledButton>
    );
}
