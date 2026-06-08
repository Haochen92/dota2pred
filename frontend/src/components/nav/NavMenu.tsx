'use client';

import { Drawer, Stack, Divider, NavLink, Burger } from '@mantine/core';
import { IconTimeline } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import { usePathname } from 'next/navigation';
import { TextMdBold, TextLgBold } from '../typography/TextVariants';
import brut from '@/styles/brutalist.module.css';

export type NavLinkItem = { href: string; label: string };

interface NavMenuProps {
  links: NavLinkItem[];
}

// Mobile navigation drawer triggered by a hamburger icon
export default function NavMenu({ links }: NavMenuProps) {
  const [opened, { open, close }] = useDisclosure(false);
  const pathname = usePathname();

  return (
    <>
      <Burger opened={opened} size="md" color="var(--mantine-color-gray-1)" onClick={open} aria-label="Open navigation menu" />
      <Drawer
        opened={opened}
        onClose={close}
        withCloseButton={false}
        padding="md"
        size={240}
        overlayProps={{ opacity: 0.55, blur: 2 }}
        title={<TextLgBold c="gray.0" tt="uppercase" style={{ letterSpacing: 1 }}>Navigation</TextLgBold>}
        styles={{
          header: {
            borderBottom: '2px solid var(--mantine-color-gray-6)',
            backgroundColor: 'var(--mantine-color-gray-9)',
            justifyContent: 'center',
            padding: 'var(--mantine-spacing-md)',
          },
          content: { backgroundColor: 'var(--mantine-color-gray-9)' },
        }}
      >
        <Stack gap="md" mt="md" justify="flex-start" p={4}>
          {links.map((l) => (
            <NavLink
              key={l.href}
              href={l.href}
              onClick={close}
              label={<TextMdBold>{l.label}</TextMdBold>}
              active={pathname === l.href}
              classNames={{ root: brut.navTile }}
            />
          ))}
          <Divider color="gray.6" my={4} />
          <NavLink
            href="/model-history"
            onClick={close}
            label={<TextMdBold>Model History</TextMdBold>}
            leftSection={<IconTimeline size={18} />}
            active={pathname === '/model-history'}
            classNames={{ root: brut.navTile }}
          />
        </Stack>
      </Drawer>
    </>
  );
}
