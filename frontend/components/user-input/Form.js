'use client';
import styled from "styled-components";
import {useState} from 'react';
import { heroData } from "./herodata";

const StyledForm = styled.form`
    display: flex;
    flex-direction: row; 
    margin: 2em;

    .formSection{
        display:flex;
        flex-direction:column;
    }
`

const InputField = ({id, name, options, handleSelect}) => {
    return(
        <div>
            <label htmlFor={id}>{name}</label>
            <select id={id} name={name} onChange={(e) => handleSelect(id, e.target.value)}>
                <option value="">Select a hero</option>
                {options.map(
                    ({hero_id, hero_name}) => (<option key={hero_id} value={hero_name}>{hero_name}</option>)
                )}
            </select>
        </div>
    )
}

export default function Form() {
    const [selected, setSelected] = useState(Array(10).fill(""));

    const handleSelection = (id, value) => {
        setSelected(prev => {
            const newSelected = [...prev];
            newSelected[id] = value;
            return newSelected;
        })    
    }

    const getFilteredOptions = (id) => {
        /*
        1. Filters array to include only values not in the selected array. 
        2. If value stored at the current index matches hero_name, it will remain visible to ensure
            that currently selected hero is still visible to the user. 
        */
        return heroData.filter(hero => !selected.includes(hero.hero_name) || selected[id] === hero.hero_name);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const data = {
            radiant:selected.slice(0, 5),
            dire: selected.slice(5, 10)
        };

        const mockFetch = () => {
            return new Promise((resolve) => {
                setTimeout(() =>
                {
                    const mockResponse = {
                        messsage:"this is a simulated async response",
                        data: data,
                        result:"success"
                    };
                    resolve(mockResponse);
                }, 2000);
            })
        }

        const result = await mockFetch();
        console.log(result);
    }

    return(
        <StyledForm onSubmit={handleSubmit}>
            <section className="formSection">
                <div> Team Radiant</div>
                {/* Each index value corresponds to the position of selected State Array*/}
                {[0, 1, 2, 3, 4].map((value, index) => (
                    <InputField
                        key={index}
                        id={value}
                        name={`radiant_hero_${index}`}
                        options={getFilteredOptions(value)}
                        handleSelect={handleSelection}
                    />
                ))}
            </section>
            <section className="formSection">
                <div>Team Dire</div>
                {[5, 6, 7, 8, 9].map((value, index) => (
                    <InputField
                        key={index}
                        id={value}
                        name={`dire_hero_${index}`}
                        options={getFilteredOptions(value)}
                        handleSelect={handleSelection}
                    />
                ))}
            </section>
            <button type="submit">Submit</button>
        </StyledForm>
    )
}