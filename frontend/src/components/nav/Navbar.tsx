import { Group, BackgroundImage, Image, Box, Tooltip, Badge, Indicator } from '@mantine/core';
import Link from 'next/link';
import { IconChevronRight } from '@tabler/icons-react';
import NavLink from './NavLink';
import ModelAccuracyDisplay from './ModelAccuracyDisplay';
import NavMenu from './NavMenu';
import { TextMdBold, TextSmRegular } from '@/components/typography/TextVariants';
import { StarMultiIcon } from '../icons/StarIcon';
import brut from '@/styles/brutalist.module.css';

// 1. Single source of truth for navigation links.
// If you add a new page, you only need to add it here.
const navLinks = [
  { href: '/match-tracker', label: 'Match Tracker' },
  { href: '/draft-predictor', label: 'Draft Predictor' },
];

export default function Navbar() {
  return (
    // 2. Use responsive props for height and padding.
    <Group
      h='100%' // Shorter height on mobile
      px={{ base: 16, sm: 160 }} // Less padding on mobile
      bg="gray.9"
      w="100%"
      maw={1600}
    >
      <Group justify="space-between" h="100%" w="100%" wrap="nowrap">
        <Group gap={0} h="100%" wrap="nowrap" align="center" hiddenFrom='sm'>
          {/* Mobile Hamburger Menu (visible ONLY on mobile) */}
          <NavMenu links={navLinks} />
        </Group>
        {/* --- Left Section (Logo & Navigation) --- */}
        <Group gap="xl" h="100%" align="center" wrap='nowrap'>

          {/* Logo (always visible, but with responsive size) */}
          <Link href="/">
            <Image
              src="/Logo.svg"
              width={210} // intrinsic SVG size (210x80): reserves aspect ratio so the LCP logo doesn't shift layout
              height={80}
              h={{ base: 60, sm: '100%' }} // CSS display size (smaller on mobile); aspect ratio held by width/height above
              w="auto"
              alt="Dota Oracle logo"
            />
          </Link>

          {/* Desktop Navigation Links (visible ONLY on desktop) */}
          <Group gap="md" visibleFrom="sm" h='100%' wrap='nowrap'>
            {navLinks.map((link) => (
              <NavLink key={link.href} href={link.href} text={link.label} />
            ))}
          </Group>
        </Group>

        {/* --- Right Section (Model Accuracy Display) --- Mobile Version */}
        <Group gap={0} h="100%" align="center" hiddenFrom='sm'>
              <Badge
                component={Link}
                href='/model-history'
                variant='filled'
                bg="gray.7"
                c="white"
                radius={8} px={10} py={6}
                h='auto'
                className={brut.badge}
                leftSection={ <StarMultiIcon size={22} /> }
                style={{ cursor: 'pointer' }}
                >
                <ModelAccuracyDisplay/>
              </Badge>
        </Group>

        {/* --- Right Section (Model Accuracy Display) --- Desktop/ Tablet Version */}
        <Group gap={0} h="100%" wrap="nowrap" align="center" visibleFrom='sm'>
          <Group
            gap={16}
            px={24}
            h="100%"
            wrap="nowrap"
            bg="gray.7"
            align="center"
          >
            <Image src="/icons/stars/star-multi.svg" height={32} width={32} alt="icon_star" />
            <Box>
              <TextMdBold>Model Accuracy</TextMdBold>
              <Link href="/model-history">
                <Group gap={4} align="center">
                  <TextSmRegular>See history</TextSmRegular>
                  <IconChevronRight size={16} />
                </Group>
              </Link>
            </Box>
          </Group>

          <BackgroundImage
            src="/bgdots.svg"
            h="100%"
            w={130}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <ModelAccuracyDisplay />
          </BackgroundImage>
        </Group>
      </Group>
    </Group>
  );
}
