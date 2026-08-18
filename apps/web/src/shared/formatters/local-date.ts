const FUSO_DO_NEGOCIO = 'America/Sao_Paulo';

/** Data civil do negócio, sem converter a meia-noite local para UTC. */
export function dataLocalHoje(agora = new Date()): string {
  const partes = new Intl.DateTimeFormat('en-US', {
    timeZone: FUSO_DO_NEGOCIO,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(agora);
  const valor = (tipo: Intl.DateTimeFormatPartTypes) =>
    partes.find((parte) => parte.type === tipo)?.value ?? '';
  return `${valor('year')}-${valor('month')}-${valor('day')}`;
}
