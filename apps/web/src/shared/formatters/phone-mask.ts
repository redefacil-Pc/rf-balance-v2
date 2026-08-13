/**
 * Máscara de telefone brasileiro, com e sem o nono dígito.
 *
 * Usada na chave PIX do tipo telefone — o legado grava `(79) 98103-1196`, e o
 * operador reconhece a chave por esse formato.
 */

const MAXIMO = 11;

export function mascararTelefone(valor: string): string {
  const d = valor.replace(/\D/g, '').slice(0, MAXIMO);

  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}
