/**
 * Formatação de dinheiro.
 *
 * A API entrega dinheiro como string decimal ("1234.56"). Este módulo apenas
 * formata: não soma, não arredonda e não converte para número para depois
 * reexibir. Qualquer aritmética financeira é responsabilidade do backend.
 */

const formatador = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// Aceita casas excedentes apenas quando são zeros de escala do Decimal da API
// (ex.: "-5000.000"). Continua rejeitando valores que exigiriam arredondamento
// no navegador, como "10.005".
const DECIMAL_VALIDO = /^-?\d+(?:\.\d{1,2}0*)?$/;

export function formatarMoeda(valorDecimal: string): string {
  if (!DECIMAL_VALIDO.test(valorDecimal)) {
    throw new Error(`valor monetário inválido: ${valorDecimal}`);
  }
  return formatador.format(Number(valorDecimal));
}

export function formatarMoedaOuVazio(valorDecimal: string | null | undefined): string {
  if (valorDecimal === null || valorDecimal === undefined || valorDecimal === '') {
    return '—';
  }
  return formatarMoeda(valorDecimal);
}
