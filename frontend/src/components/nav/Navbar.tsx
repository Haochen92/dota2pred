import { Group, Stack, BackgroundImage, Center, Title } from '@mantine/core'
import Image from 'next/image'
import Link from 'next/link'
import { IconChevronRight } from '@tabler/icons-react'
import NavLink from './NavLink'
import { TextMdBold, TextSmRegular } from '@/components/typography/TextVariants'

export default function Navbar() {
  return (
    <Group h={80} px={160} bg="gray.9" gap={16} w="100%" wrap="nowrap" justify="space-between">
      <Group gap={48} align="center" h="100%" wrap="nowrap">
        <Image src="/Logo.svg" height={80} width={210} alt="logo" />
        <Group wrap="nowrap" h="100%" gap="md">
          <NavLink href="/match-tracker" text="Match Tracker" />
          <NavLink href="/draft-predictor" text="Draft Predictor" />
        </Group>
      </Group>

      <Group gap={0} h="100%" wrap="nowrap">
        <Group gap={16} px={24} h="100%" wrap="nowrap" bg="gray.7">
          <Image src="/icons/stars/star-multi.svg" height={32} width={32} alt="icon_star" />
          <Group c="white">
            <Stack gap={0} align="flex-start">
              <TextMdBold>Model Accuracy</TextMdBold>
              <Link href="/dashboard">
                <Group gap={4}>
                  <TextSmRegular>See history</TextSmRegular>
                  <IconChevronRight size={16} />
                </Group>
              </Link>
            </Stack>
          </Group>
        </Group>

        <BackgroundImage src="/bgdots.svg" h="100%" w={130}>
          <Center h="100%" w="100%">
            <Title order={4} fw={500} c='black'>62%</Title>
          </Center>
        </BackgroundImage>
      </Group>
    </Group>
  )
}
