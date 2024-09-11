"use client";

import styled from "styled-components";
import MatchContainer from "./@matches/page";
import Dashboard from "./@dashboard/layout";
import UserInput from "./@userinput/page";
import Practice from "practice/Practice";

const StyledHome = styled.main`
  display: flex;
  flex-direction: column;
  background-color:${({theme}) => theme.getColor('black-alpha', 500)};
  height: auto;
  align-items: center;
  max-width:${({theme}) => theme.widthConfig.max};
`

export default function Home() {
  return (
    <StyledHome>
      <MatchContainer/>
      <Dashboard/>
      <UserInput/>
      {/* <Practice/> */}
    </StyledHome>
  )
}
