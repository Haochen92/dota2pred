import ModelHistoryClient from "./_components/ModelHistoryClient";

export const metadata = {
  title: 'Model History',
  description: 'Model performance over time: accuracy, AUC, calibration, and Brier score.',
};

export default function ModelHistoryPage() {
    return <ModelHistoryClient />;
}
