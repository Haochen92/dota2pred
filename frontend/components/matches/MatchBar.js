import styled from "styled-components";

const StyledMatchBar = styled.div`
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
`

const StyledBar = styled.div`
    display:flex;
    flex-direction:row;
    align-items: stretch;
`

const StyledTime = styled.div`
    color:${({theme}) => theme.getColor("white-alpha", 500)};
`

const StyledTournament = styled.div`
    color:${({theme}) => theme.getColor("red", 500)};
`

const StyledRadiant = styled.div`
    color:black;
    background-color: ${({theme}) => theme.getColor("green", 500)}
`

const StyledDire = styled.div`
    color:black;
    background-color: ${({theme}) => theme.getColor("red", 500)}
`

export default function MatchBar({time, tournament, radiant, dire}) {
    return(
        <StyledMatchBar>
            <StyledBar>
                <StyledTime>{time}</StyledTime>
                <StyledTournament>{tournament}</StyledTournament>
            </StyledBar>
            <StyledBar>
                <StyledRadiant>{radiant}</StyledRadiant>
                <StyledDire>{dire}</StyledDire>
            </StyledBar>
        </StyledMatchBar>
    )
}