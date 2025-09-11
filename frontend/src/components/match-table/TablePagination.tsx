import { Group, Pagination } from "@mantine/core";

type PaginationProps = {
  page: number;
  totalPages: number;
  hasNext?: boolean;
  hasPrevious?: boolean;
  onPageChange: (page: number) => void;
  pageSize?: number;
};

export default function TablePagination({
  page,
  totalPages,
  onPageChange,
}: PaginationProps) {
  return (
    <Group justify="center" gap="md">
      <Pagination value={page} total={Math.max(totalPages, 1)} onChange={onPageChange}  />
    </Group>
  );
}
