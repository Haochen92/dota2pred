'use client';

import {  Drawer, Stack, Divider, NavLink, Burger, MantineTheme, Title } from '@mantine/core';
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
        styles={(theme: MantineTheme) => ({
            header: {
                        borderBottom: `1px solid ${theme.colors.gray[7]}`,
                        backgroundColor: theme.colors.gray[9],
                        justifyContent: 'center',
                        padding: theme.spacing.md
            },
            content: { backgroundColor: theme.colors.gray[9] }
        })}
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
          <Divider/>
        </Stack>
      </Drawer>
    </>
  );
}
