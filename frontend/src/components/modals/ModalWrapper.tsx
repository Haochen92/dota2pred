'use client';

import { Modal, Paper } from '@mantine/core';
import { useRouter } from 'next/navigation';

export default function ModalWrapper({children}: {children: React.ReactNode}) {
    const router = useRouter();

    return (
            <Modal
                id='modal-wrapper'
                opened={true}
                onClose={() => router.back()}
                centered size='55rem'
                withCloseButton={false}
                padding='0'
            >
                {children}
            </Modal>
    )
}
