import { Group, Stack, Text, BackgroundImage } from '@mantine/core'
import Image from 'next/image'
import Link from 'next/link'
import { IconChevronRight } from '@tabler/icons-react'
import NavLink from './NavLink'
import classes from './Navbar.module.css'

export default function Navbar() {

    return(
        <Group className={classes.main}>
            <Group className={classes.container}>
                <Group className={classes.navContainer}>
                    <Image
                        src='/Logo.svg'
                        height={80}
                        width={210}
                        alt='logo'
                    />
                    <Group wrap='nowrap' h='100%'>
                        <NavLink href='/matches'text='Live predictions'/>
                        <NavLink href='/simulator' text='Match simulator'/>
                    </Group>
                </Group>
                <Group className={classes.modelContainer} h='100%' wrap='nowrap'>
                    <Group className={classes.leftContainer} h='100%' wrap='nowrap'>
                        <Image src='/icons/stars/star-multi.svg' height='32' width='32' alt='icon_star'/>
                        <Group c='white' >
                            <Stack className={classes.leftStack} align='flex-start'>
                                <Text fz='15' lh='lg' fw={700}>Model Accuracy</Text>
                                <Link href='/dashboard'>
                                    <Group>
                                        <Text fz='14' lh='lg' fw={400}>See history</Text>
                                        <IconChevronRight size={16}/>
                                    </Group>
                                </Link>
                            </Stack>
                        </Group>
                    </Group>
                    <BackgroundImage src='/bgdots.svg' className={classes.rightContainer}>
                        <Text fz='32' lh='1.3' fw={500}>62%</Text>
                    </BackgroundImage>
                </Group>
            </Group>
        </Group>
    )
}