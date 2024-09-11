'use client';
import styled from "styled-components";
import { useState, useEffect } from "react";
import Skeleton, {SkeletonTheme} from "react-loading-skeleton";
import 'react-loading-skeleton/dist/skeleton.css';

const StyledContainer = styled.div`
    height:800px;
    width:600px;
    border: 3px solid black;
    display: flex;
    flex-direction: column;
`

const EventListenerBox = ({callback}) => {
    return(
        <button onClick={callback}> Click me </button>
    )
}

const ToDoList = () => {
    const [items, setItems] = useState([]);
    const [inputValue, setInputValue] = useState("");
    const addItem = (e) => {
        e.preventDefault();
        if (inputValue.trim() !== "") {
            setItems(prev => [...prev, inputValue]);
            setInputValue("");
        }
    }

    const deleteItem = (index) => {
        setItems((prev) => prev.filter((item, i) => i !== index));
    }

    return(
        <div>
        <ul>
            {items.map((item, index) => (    
                    <li key={index}>{item}
                        <button onClick={() => deleteItem(index)}> x </button>
                    </li>     
            ))}
        </ul>
        <form onSubmit={addItem}>
            <input value={inputValue} onChange={(e) => setInputValue(e.target.value)}></input>
            <button type="Submit">Add Item</button>
        </form>
        </div>
    )
}

const FormBox = () => {

    const [userInput, setUserInput] = useState({
        username:"",
        password:"",
        email:""
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        console.log(userInput);
        setUserInput({username:"",
        password:"",
        email:""});
    }

    const handleChange = (e) => {
        const {name, value} = e.target;
        setUserInput((prev) => ({...prev, [name]:value}));
    }

    return (
        <form  onSubmit={handleSubmit}>
            <label htmlFor="username"> Username</label>
            <input name="username" required={true} placeholder="Cuteflygon" id="username" value={userInput.username} onChange={handleChange}></input>
            <label htmlFor="password"> Password</label>
            <input type="password" name="password" required={true} placeholder="1234!" id="password" value={userInput.password} onChange={handleChange}></input>
            <label htmlFor="email"> Email</label>
            <input type="email" name="email" required={true} placeholder="gengie@gmail.com" id="email" value={userInput.email} onChange={handleChange}></input>
            <button type="submit">Submit</button>
        </form>
    )
}

const SelectionBox = () => {
    const fruits = ["apple", "pear", "watermelon", "peach", "cherry", "guava", "durian", "mango", "banana"]
    const [selection, setSelection] = useState(new Array(5).fill(""))

    const handleChange = (e, index) => {
        setSelection(prev => {
            const newArray = [...prev];
            newArray[index] = e.target.value;
            return newArray;
        })
    }

    const handleSubmit = (e) => {
        e.preventDefault();
        console.log(selection);
    }

    return(
        <form onSubmit={handleSubmit}>
            {[0,1,2,3,4].map((value, index) => (
                <div key={index}>
                    <label name={index}>{value}</label>
                    <select id={index} onChange={(e) => handleChange(e, index)}>
                    <option value=""> Select an option</option>
                    {fruits.map((value, index) => 
                    <option key={index} value={value}> {value} </option>)}
                    </select>
                </div>
            )         
             )}
            <button type="submit" > Submit </button>
        </form> 
    )
}

const DynamicFields = () => {
    const [dynamicList, setDynamicList] = useState({});
    const [field, setField] = useState("");

    const handleInput = (e) => {
        setField(e.target.value);
    }

    const handleFieldInput = (e, item) => {
        setDynamicList((prev) => {
            const newList = {...prev, [item]:e.target.value};
            return newList;
        })
    }

    const handleSubmit = (e) =>  {
        /* print the existing key value pairs in Dynamic List and reset all the values to empty string */
        e.preventDefault();
        console.log(dynamicList);
        setDynamicList(prev => {
            const newObj = {...prev};
            Object.keys(newObj).forEach(
                key => {
                    newObj[key] = "";
                }
            )
            return newObj;
        })
    }

    const addField = (e) => {
        e.preventDefault();
        if (field.trim() === "") {return;}

        setDynamicList((prev) => ({...prev, [field]:""}));
        setField("");
    }

    const deleteField = (e,fieldName) => {
        e.preventDefault();
        setDynamicList(prev => {
            const newObj = {...prev};
            delete newObj[fieldName];
            return newObj;
        })
    }
    
    return (
        <form onSubmit={handleSubmit}>
            {Object.keys(dynamicList).map((item, index) => (
                <div key={item}>
                    <label htmlFor={item}> {item} </label>
                    <input id={item} value={dynamicList[item]} onChange={(e) => handleFieldInput(e, item)}></input>
                    <button type="button" onClick={(e) => deleteField(e,item)}> x </button>
                </div>  
            ))}
            <input onChange={handleInput} value={field}></input>
            <button type="button" onClick={addField}> Add Field </button>
            <button type="submit"> Submit Form </button>
        </form> 
    )
}

const LoadingSkeleton = () => {
    return(
        <SkeletonTheme baseColor="#202020" highlightColor="#444">
            <p>
                <skeleton count={3}></skeleton>
            </p>
        </SkeletonTheme>
    )
}

const Pokemon = () => {
    const endPoint = "https://pokeapi.co/api/v2/pokemon/?limit=20&offset=0";
    const [data, updateData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [images, setImages] = useState({});
    const itemsPerPage = 4;
    

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch(endPoint);
                const jsonData = await res.json();
                updateData(jsonData.results);
                console.log(jsonData.results);
                
            } catch (error) {
                console.error('Error fetching pokemon list:', error);
            } finally {
                setLoading(false);
            }
        }
    
        fetchData();
    },[]);

    const goNextPage = () => {
        if (page >= totalPages){
            return;
        }
        setPage(prev => prev + 1);
    }

    const goPrevPage = () => {
        if (page <= 0) {
            return;
        }
        setPage(prev => prev - 1);
    }
    const totalPages = Math.ceil(data.length/itemsPerPage);

    useEffect(() => {
        // Fetch images for the current page
        const fetchImages = async () => {
            const currentPageItems = data.slice(page * itemsPerPage, (page + 1) * itemsPerPage);
            const newImages = {};

            await Promise.all(
                currentPageItems.map(async (item) => {
                    if (!images[item.name]) { // Only fetch if the image is not already fetched
                        const res = await fetch(`https://pokeapi.co/api/v2/pokemon/${item.name}`);
                        const pokemonData = await res.json();
                        newImages[item.name] = pokemonData.sprites.front_default;
                    }
                })
            );

            setImages((prevImages) => ({ ...prevImages, ...newImages }));
        };

        if (data.length > 0) {
            fetchImages();
        }
    }, [page, data]);

    

    return(
        <div>
            {loading ? <LoadingSkeleton /> : data.slice(page * itemsPerPage, (page + 1) * itemsPerPage).map((item, index) => (
                <div key={index}>
                    <div>{item.name}</div>
                    <img src={images[item.name]} alt={item.name}/>
                </div>
            ))}
            <div>
                <button onClick={goNextPage} disabled={page >= totalPages - 1 ? true:false}> Go Next</button>
                <div>Page {page} of {totalPages}</div>
                <button onClick={goPrevPage} disabled={page <= 0 ? true: false}>Go Prev</button>
            </div>
        </div>
    )
}

export default function Practice(){
    const [time, setTime] = useState(0);
    const [count, setCounter] = useState(0);

    const increaseCounter = () => {
        setCounter(prev => prev + 1)
    }

    useEffect(() => {
        const interval = setInterval(() => setTime(prev => prev + 1), 1000);
        return () => clearInterval(interval);
    }, [])


    return(
        <StyledContainer>
            {time}
            <EventListenerBox callback={increaseCounter}/>
            <div>{count}</div>
            <FormBox></FormBox>
            <SelectionBox></SelectionBox>
            <ToDoList></ToDoList>
            <DynamicFields></DynamicFields>
            <Pokemon></Pokemon>
        </StyledContainer>
    )
}

export {Pokemon};