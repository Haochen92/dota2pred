"use client";
import styled from "styled-components";

const StyledLoading = styled.div`
    color:red;
`

export default function Loading() {
    return(
        <StyledLoading>
            Loading... Please wait
        </StyledLoading>
    )
}