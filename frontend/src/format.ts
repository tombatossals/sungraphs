export function formatProduction(totalWh: number | null | undefined) {
  if (typeof totalWh !== "number") {
    return "Sin datos";
  }

  if (totalWh >= 1000) {
    return `${new Intl.NumberFormat("es-ES", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(totalWh / 1000)} kWh`;
  }

  return `${new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 0
  }).format(totalWh)} Wh`;
}

export function formatDisplayDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(new Date(`${value}T00:00:00`));
}

export function formatCO2(kg: number): string {
  return kg >= 1000
    ? `${(kg / 1000).toFixed(2)} t`
    : `${kg.toFixed(1)} kg`;
}
