import React from 'react';
import styled from 'styled-components';
import DataTable from 'react-data-table-component';
import { tabledata } from './tabledata'; // Ensure tabledata is correctly imported

const StyledTable = styled.div`
  .rdt_Table {
    font-family: Arial, sans-serif;
    font-size: 14px;
  }
  .rdt_TableHeadRow {
    background: #f5f5f5;
  }
  .rdt_TableCell {
    border-right: 1px solid #ddd;
  }
`;

const columns = [
  {
    name: 'Time',
    selector: row => row.time,
    sortable: true,
  },
  {
    name: 'Model Prediction',
    selector: row => row.model_prediction,
    sortable: true,
    filterable: true,
  },
  {
    name: 'Outcome',
    selector: row => row.outcome,
    sortable: true,
    filterable: true,
  },
  {
    name: 'Radiant',
    selector: row => row.radiant,
    sortable: true,
  },
  {
    name: 'Dire',
    selector: row => row.dire,
    sortable: true,
  },
  {
    name: 'Tournament',
    selector: row => row.tournament,
    sortable: true,
  },
];

const TabulatorComponent = () => {
  return (
    <StyledTable>
      <DataTable
        title="Match Data"
        columns={columns}
        data={tabledata}
        pagination
        paginationPerPage={5}
        paginationRowsPerPageOptions={[5, 10, 20]}
        defaultSortField="time"
      />
    </StyledTable>
  );
};

export default TabulatorComponent;

