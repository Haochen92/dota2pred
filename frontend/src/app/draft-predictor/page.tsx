import DraftPredictorClient from "./_components/DraftPredictorClient"

export const metadata = {
  title: 'Draft Predictor',
  description: 'Pick a Dota 2 draft and get an instant win-probability prediction.',
};

export default function SimulatorPage(){
    return(
          <DraftPredictorClient />
    )
}
