'use client';

import { Modal, Group, Title } from '@mantine/core';
import { useRouter } from 'next/navigation';
import { TextLgBold } from '@/components/typography/TextVariants';

export default function ModalWrapper({children}: {children: React.ReactNode}) {
    const router = useRouter();

    return (
            <Modal.Root opened={true} onClose={() => router.back()} centered size='55rem' padding='0' >
                <Modal.Overlay />
                <Modal.Content radius={12} style={{ overflowY: 'auto', overflowX:'hidden'}}>
                    <Modal.Header p='0' w='100%'>
                        <Group justify='space-between' align='center' p='xl' w='100%' bg='gray.8'>
                            {/* Desktop Title */}
                            <Title order={4} c='white' visibleFrom='sm'>Model Performance History</Title>
                            {/* Mobile Title */}
                            <TextLgBold c='white' hiddenFrom='sm'>Model Performance History</TextLgBold>
                            <Modal.CloseButton />
                        </Group>
                    </Modal.Header>
                    <Modal.Body>
                        {children}
                    </Modal.Body>
                </Modal.Content>
            </Modal.Root>
    )
}
