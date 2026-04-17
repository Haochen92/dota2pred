import { Group, Skeleton, Stack } from "@mantine/core";

export default function PredictionDetailsSkeleton({ mode = "modal" }: { mode?: "modal" | "mobile" }) {
  const isMobile = mode === "mobile";

  return (
    <Group p="md" justify="center" w="100%">
      <Stack justify="center" align="center" w={isMobile ? 300 : 800}>
        <Group justify="space-between" align="center" mb="md" w="100%" px={isMobile ? 0 : "md"}>
          <Group gap="sm">
            <Group gap={6} align="center">
              <Skeleton height={24} width={24} radius="xl" />
              <Skeleton height={14} width={60} />
            </Group>
            <Group gap={6} align="center">
              <Skeleton height={24} width={24} radius="xl" />
              <Skeleton height={14} width={48} />
            </Group>
          </Group>
          <Skeleton height={28} width={110} radius="xl" />
        </Group>

        <Skeleton height={isMobile ? 200 : 400} width="100%" radius="md" />
      </Stack>
    </Group>
  );
}
