'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import classes from './NavLink.module.css'
import { Anchor, AnchorProps } from '@mantine/core';
import { TextMdMedium } from '@/components/typography/TextVariants';

interface NavLinkProps extends Omit<AnchorProps, 'href'> {
  href: string;
  text: string;
}

export default function NavLink({ href, text, ...props }: NavLinkProps) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Anchor
      component={Link}
      href={href}
      c={isActive ? 'primary' : 'white'}
      className={`${classes.link} ${isActive ? classes.active : ''}`}
      {...props}
    >
      <TextMdMedium component="span">{text}</TextMdMedium>
    </Anchor>
  );
}
