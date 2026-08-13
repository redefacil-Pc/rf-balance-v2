/**
 * Máscara de valor monetário na digitação.
 *
 * O operador digita apenas dígitos e o valor cresce da direita para a esquerda:
 * `1462964` vira `14.629,64`. É o comportamento consagrado em sistema financeiro
 * brasileiro e elimina a dúvida de onde vai o separador decimal — que, em campo
 * de dinheiro, é a diferença entre R$ 100,00 e R$ 10.000,00.
 *
 * `paraDecimal` devolve a string decimal que a API espera (`"14629.64"`). Nada
 * aqui vira `number`: dinheiro atravessa o frontend como texto, sempre.
 */

const CASAS = 2;
//: mais que isto não é digitação, é colagem de lixo — e estoura DECIMAL(18,2)
const MAXIMO_DE_DIGITOS = 16;

export function mascararMoeda(valor: string): string {
  const digitos = valor.replace(/\D/g, '').slice(0, MAXIMO_DE_DIGITOS);
  if (digitos === '') {
    return '';
  }

  const preenchido = digitos.padStart(CASAS + 1, '0');
  const inteiros = preenchido.slice(0, -CASAS).replace(/^0+(?=\d)/, '');
  const centavos = preenchido.slice(-CASAS);

  return `${agruparMilhares(inteiros)},${centavos}`;
}

/** `"14.629,64"` → `"14629.64"`; vazio devolve vazio, para o schema reclamar. */
export function moedaParaDecimal(mascarado: string): string {
  const digitos = mascarado.replace(/\D/g, '');
  if (digitos === '') {
    return '';
  }
  const preenchido = digitos.padStart(CASAS + 1, '0');
  return `${preenchido.slice(0, -CASAS)}.${preenchido.slice(-CASAS)}`;
}

/** `"14629.64"` → `"14.629,64"`, para preencher o formulário de edição. */
export function decimalParaMoeda(decimal: string): string {
  return mascararMoeda(decimal.replace(/\D/g, ''));
}

function agruparMilhares(inteiros: string): string {
  return inteiros.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
