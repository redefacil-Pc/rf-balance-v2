/**
 * Máscara de percentual (TPS).
 *
 * Diferente da máscara de dinheiro, aqui a digitação é natural: `12,5` é
 * exatamente o que o operador escreve. Percentual é dito em unidades, não em
 * centésimos, e forçar `1250` → `12,50` só confundiria.
 *
 * A máscara **não** impede digitar acima de 100. Bloquear silenciosamente deixa
 * o operador sem entender por que o campo não aceita; quem recusa é a validação,
 * com mensagem. A máscara só garante que o texto seja um número.
 */

//: a coluna é DECIMAL(9,6) — seis casas comportam fração de ponto percentual
const CASAS = 6;
const INTEIROS = 3;

export function mascararPercentual(valor: string): string {
  const limpo = valor.replace(/[^\d,.]/g, '').replace(/\./g, ',');
  const [inteiros = '', ...resto] = limpo.split(',');

  const parteInteira = inteiros.slice(0, INTEIROS);
  if (resto.length === 0) {
    return parteInteira;
  }
  // vírgulas extras são ignoradas, não viram separador novo
  return `${parteInteira},${resto.join('').slice(0, CASAS)}`;
}

/** `"12,5"` → `"12.5"`; vazio devolve vazio, para o schema reclamar. */
export function percentualParaDecimal(mascarado: string): string {
  const normalizado = mascarado.replace(',', '.');
  return normalizado === '.' ? '' : normalizado;
}

/** `"30.000000"` → `"30"`, para preencher o formulário sem zeros inúteis. */
export function decimalParaPercentual(decimal: string): string {
  if (!decimal.includes('.')) {
    return mascararPercentual(decimal);
  }
  const enxuto = decimal.replace(/0+$/, '').replace(/\.$/, '');
  return mascararPercentual(enxuto);
}
