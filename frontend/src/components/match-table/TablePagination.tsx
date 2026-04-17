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
      {/* Desktop pagination view */}
      <Pagination value={page} total={Math.max(totalPages, 1)} onChange={onPageChange} visibleFrom="sm" />
      {/* Mobile Pagination view */}
      <Pagination value={page} total={Math.max(totalPages, 1)} onChange={onPageChange} siblings={0} hiddenFrom="sm"/>
    </Group>
  );
}
