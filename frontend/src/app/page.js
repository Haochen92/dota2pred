'use client';

import Navbar from "@/components/nav/Navbar";
import { AppShell } from "@mantine/core";

export default function Home({children}) {
  return (
    <AppShell
      header={{height:80, offset:true}}
    >
      <AppShell.Header>
        <Navbar/>
      </AppShell.Header>
      <AppShell.Main h='100vh' style={{backgroundColor:'var(--blue-100)'}}>
        {children}
      </AppShell.Main>
    </AppShell>
  );
}
