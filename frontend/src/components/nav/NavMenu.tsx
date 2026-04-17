'use client';

import {  Drawer, Stack, Divider, NavLink, Burger } from '@mantine/core';
import { IconTimeline } from '@tabler/icons-react';
import { useDisclosure } from '@mantine/hooks';
import { usePathname } from 'next/navigation';
import { TextMdRegular, TextLgBold } from '../typography/TextVariants';

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
      <Burger opened={opened} size="md" onClick={open} />
      <Drawer
        opened={opened}
        onClose={close}
        withCloseButton={false}
        padding="md"
        size={200}
        overlayProps={{ opacity: 0.45, blur: 2 }}
        title={<TextLgBold c='gray.1'>Navigation</TextLgBold>}
        styles={{
          header: {
            borderBottom: '1px solid var(--mantine-color-gray-7)',
            backgroundColor: 'var(--mantine-color-gray-9)',
            justifyContent: 'center',
            padding: 'var(--mantine-spacing-md)'
          },
          content: { backgroundColor: 'var(--mantine-color-gray-9)' }
        }}
        >
        <Stack gap="sm" mt="sm" justify='flex-start' p={4}>
          {links.map((l) => (
            <NavLink
              key={l.href}
              href={l.href}
              label={<TextMdRegular>{l.label}</TextMdRegular>}
              variant='light'
              active={pathname === l.href}
            />
          ))}
          <Divider />
          <NavLink
            href='/model-history'
            label={<TextMdRegular>Model History</TextMdRegular>}
            leftSection={<IconTimeline size={16} />}
            variant='filled'
            color='grape'
            active={pathname === '/model-history'}
            style={{ borderRadius: 8 }}
          />
        </Stack>
      </Drawer>
    </>
  );
}
