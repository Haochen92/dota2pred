import dynamic from 'next/dynamic';

const Chart = dynamic(() => import('components/dashboard/graph/Chart'), {ssr: false,});

const Graph = () => {
    return(
        <div>
            <h1>My Bar Chart</h1>
            <Chart />
        </div>
    )
};

export default Graph;
