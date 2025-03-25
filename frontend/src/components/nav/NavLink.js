'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import classes from './NavLink.module.css'
import { Text } from '@mantine/core';

export default function NavLink({ href, text, ...props }) {
  const pathname = usePathname();
  const isActive = pathname === href;
  return (
    <Link
      href={href}
      {...props}
      className={`${classes.link} ${isActive ? classes.active : ''}`}
    >
      <Text fz={18} fw={500} lh='lg'>{text}</Text>
    </Link>
  );
}
