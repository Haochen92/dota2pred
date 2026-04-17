'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import classes from './NavLink.module.css'
import { Anchor } from '@mantine/core';
import { TextLgBold } from '@/components/typography/TextVariants';

interface NavLinkProps {
  href: string;
  text: string;
}

export default function NavLink({ href, text }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Anchor
      component={Link}
      href={href}
      className={`${classes.link} ${isActive ? classes.active : ''}`}
    >
      <TextLgBold component="span">{text}</TextLgBold>
    </Anchor>
  );
}
