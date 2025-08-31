import { create } from "zustand";
import { HeroImageData } from "@/types/contracts";
import fetchHeroData  from "@/api/fetch-hero-data";

interface HeroStoreState {
    heroes: HeroImageData[];
    isLoading: boolean;
    hasFetched: boolean;
    error: Error | null;
    fetchHeroes: () => Promise<void>;
}

export const useHeroStore = create<HeroStoreState>((set, get) => ({
    heroes: [],
    isLoading: false,
    hasFetched: false,
    error: null,

    fetchHeroes: async () => {
        const { hasFetched, isLoading } = get();

        // If data is already fetched or a fetch is in progress, do nothing.
        if (hasFetched || isLoading) {
            return;
        }

        set({ isLoading: true, error: null });
        try {
            const heroDataArray = await fetchHeroData();

            set({
                heroes: heroDataArray,
                isLoading: false,
                hasFetched: true
            });
        } catch (error: any) {
            console.error("Failed to fetch heroes for store:", error);
            set({ error, isLoading: false, hasFetched: false }); // Reset to allow retries
        }
    },
}));



(async() => {
    const heroStore = useHeroStore.getState();
    await heroStore.fetchHeroes();
    const updatedHeroes = useHeroStore.getState().heroes;
    console.log("Fetched heroes:", updatedHeroes);
})().catch(error => {
    console.error("\n--- An unexpected error occurred ---");
    console.error(error);
    process.exit(1);
});
