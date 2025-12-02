import { useContext } from "react";
import { DraftContext } from "@/context/DraftContext";

export default function useDraftContext() {
    const context = useContext(DraftContext);

    if (context === null) {
        throw new Error('useDraftContext must be used within a DraftProvider');
    }

    return context;
}
