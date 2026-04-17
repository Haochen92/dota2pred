import { useDisclosure } from "@mantine/hooks";
import { Modal, Button, Paper, Group, Tooltip, Title} from "@mantine/core";
import PredictionDetailsClient from "@/components/prediction-details/PredictionDetailsClient";
import { TextMdBold } from "@/components/typography/TextVariants";

export default function PredictionDetailsModal({ children, match_id }: { children: React.ReactNode, match_id: number }) {
    const [opened, { open, close }] = useDisclosure(false);

    return (
        <>
            <Modal.Root opened={opened} onClose={close} size="800px" padding='0' centered>
                <Modal.Overlay/>
                <Modal.Content radius={12} style={{ overflowY: 'auto', overflowX:'hidden' }} p={0}>
                    <Modal.Header p='16' w='100%' bg='gray.8'>
                        <Group justify='space-between' align='center' p='xs' w='100%' bg='gray.8'>
                            <Title order={4} c='white'>Prediction Details</Title>
                            <Modal.CloseButton />
                        </Group>
                    </Modal.Header>
                    <Modal.Body bg='gray.7' p={0}>
                        <Paper p={0} shadow='sm' radius='md' bg='gray.7' w='100%'>
                            <PredictionDetailsClient matchId={match_id} mode="modal" />
                        </Paper>
                    </Modal.Body>
                </Modal.Content>
            </Modal.Root>
            <Tooltip label="View Prediction Info" withArrow>
                <Button variant='transparent' onClick={open}>{children}</Button>
            </Tooltip>
        </>
    )
}
