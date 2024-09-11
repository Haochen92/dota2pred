"use client";
import styled from "styled-components";
import MatchBar from "components/matches/MatchBar";
import { dataList } from "components/matches/dataList";
import { useState } from "react";

const StyledContainer = styled.main`
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: ${({theme}) => theme.getColor('blue', 500)};
    max-width: 700px;
    width: 700px;
    height: 500px;
    border:2px, solid, black;
    padding:4px;
    overflow: hidden;
`

const PaginationControls = styled.div`
    display:flex;
    justify-content: center;
    margin: 10px 0;
`

const Button = styled.button`
      margin: 0 5px;
  padding: 5px 10px;
  background-color: ${({ theme }) => theme.getColor('blue', 300)};
  border: none;
  border-radius: 5px;
  color: white;
  cursor: pointer;

  &:disabled {
    background-color: ${({ theme }) => theme.getColor('gray', 300)};
    cursor: not-allowed;
  }
`

export default function MatchContainer({...props}) {
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 3;
    const totalPages = Math.ceil(dataList.length / itemsPerPage);
    const currentItems = dataList.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

    const goNextPage = () => {
        setCurrentPage((prev) => Math.min(prev + 1, totalPages));
    }

    const goPrevPage = () => {
        setCurrentPage((prev) => Math.max(prev - 1, 1));
    }

    return(
        <StyledContainer>
            {currentItems.map((match, index) => (
                <MatchBar 
                    key={index} 
                    time={match.time} 
                    tournament={match.tournament} 
                    radiant={match.radiant} 
                    dire={match.dire}/>)
            )}
            <PaginationControls>
                <Button onClick={goPrevPage} disabled={currentPage === 1}>
                    Previous
                </Button>
                <span>
                    Page {currentPage} of {totalPages}
                </span>
                <Button onClick={goNextPage} disabled={currentPage === totalPages}>
                    Next
                </Button>
            </PaginationControls>
        </StyledContainer>
    )
}