'use client';

import { Modal, Group, Title } from '@mantine/core';
import { useRouter } from 'next/navigation';

const ModalHeader = () => {
    return (
        <Group justify='flex-start' px={8} >
            <Title order={3} c='white'>Model Performance History</Title>
        </Group>
    );
}



export default function ModalWrapper({children}: {children: React.ReactNode}) {
    const router = useRouter();

    return (
            <Modal.Root opened={true} onClose={() => router.back()} centered size='55rem' padding='0' >
                <Modal.Overlay />
                <Modal.Content radius={12} style={{ overflowY: 'auto', overflowX:'hidden'}}>
                    <Modal.Header p='0' w='100%'>
                        <Group justify='space-between' align='center' p='xl' w='100%' bg='gray.8'>
                            <Title order={4} c='white'>Model Performance History</Title>
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
