import Header from "./components/Header";
import ProductionHeatmap from "./components/ProductionHeatmap";
import InverterStats from "./components/InverterStats";
import VictronStats from "./components/VictronStats";
import { useSolarData } from "./useSolarData";

export default function App() {
  const {
    history,
    historyLoading,
    historyError,
    dailyData,
    date,
    setDate,
    selectedHistoryEntry,
    metadata,
  } = useSolarData();

  return (
    <>
      <Header />
      <div className="w-4/5 mx-auto flex flex-col gap-y-2 pb-6">
        {historyLoading ? (
          <p className="p-4 text-center text-sm text-[color:var(--text-soft)]">Cargando...</p>
        ) : historyError ? (
          <p className="p-4 text-center text-sm text-red-600">{historyError}</p>
        ) : (
          history.length > 0 && (
            <ProductionHeatmap
              data={history}
              selectedDate={date}
              onSelectDate={setDate}
            />
          )
        )}
        <InverterStats entry={selectedHistoryEntry} dailyData={dailyData} metadata={metadata} />
        {dailyData && Object.keys(dailyData).some(k => k.startsWith("victron1-")) && (
          <VictronStats dailyData={dailyData} metadata={metadata} />
        )}
      </div>
    </>
  );
}
