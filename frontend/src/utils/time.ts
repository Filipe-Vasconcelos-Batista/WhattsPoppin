const WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const DAY_MS = 24 * 60 * 60 * 1000;

function formatClock(date: Date): string {
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${hours}:${minutes}`;
}

export function formatTimeNow(): string {
  return formatClock(new Date());
}

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

/** Hora na lista de conversas: hoje "14:32", ontem "Ontem", na última
 * semana o dia ("Ter"), antes disso a data ("03/09"). */
export function formatListTime(sentAt: number, now: Date = new Date()): string {
  const date = new Date(sentAt);
  const daysAgo = Math.round((startOfDay(now) - startOfDay(date)) / DAY_MS);

  if (daysAgo <= 0) return formatClock(date);
  if (daysAgo === 1) return 'Ontem';
  if (daysAgo < 7) return WEEKDAYS[date.getDay()];

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  return `${day}/${month}`;
}
