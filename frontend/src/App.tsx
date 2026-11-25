import Header from "./components/Header";
import ProductionHeatmap from "./components/ProductionHeatmap";
import InverterStats from "./components/InverterStats";
import VictronStats from "./components/VictronStats";
import EnergyFlowChart from "./components/EnergyFlowChart";
import CameraTimelapse from "./components/CameraTimelapse";
import { useSolarData } from "./useSolarData";
import { useCallback, useState } from "react";

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
  const [camera, setCamera] = useState<{ date: string; time: string | null }>({ date: "", time: null });
  const onCameraTime = useCallback((time: string | null) => setCamera({ date, time }), [date]);
  const markerTime = camera.date === date ? camera.time : null;

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
        <CameraTimelapse key={date} date={date} onTimeChange={onCameraTime} />
        {dailyData && Object.keys(dailyData).some(k => k.startsWith("victron1-") || k.startsWith("shelly1-")) && (
          <VictronStats dailyData={dailyData} metadata={metadata} />
        )}
        <EnergyFlowChart dailyData={dailyData} metadata={metadata} markerTime={markerTime} />
      </div>
    </>
  );
}
