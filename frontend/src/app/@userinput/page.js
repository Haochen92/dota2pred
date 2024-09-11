'use client';

import styled from "styled-components";
import Form from "components/user-input/Form";

const StyledContainer = styled.div`
    display: flex;
    justify-content: center;
`

export default function UserInput() {
    return(
        <StyledContainer>
            <Form></Form>
        </StyledContainer>
    )
}