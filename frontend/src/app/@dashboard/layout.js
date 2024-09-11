"use client";

import DashboardLayout from "components/dashboard/DashboardLayout";
import Table from "./@table/page";
import Graph from "./@graph/page";

export default function Dashboard(){
    return(
        <DashboardLayout>
            <Table/>
            <Graph/>
        </DashboardLayout>
    )
}