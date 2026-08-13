/**
 * Máscara de CPF e CNPJ.
 *
 * A máscara é progressiva: formata o que já foi digitado e escolhe o formato
 * pela quantidade de dígitos, sem exigir que o operador diga de antemão se é
 * pessoa física ou jurídica.
 *
 * Só apresentação. O dígito verificador é validado no backend, que é onde a
 * unicidade do cadastro é decidida — máscara não valida documento.
 */

const DIGITOS_DE_CPF = 11;
const DIGITOS_DE_CNPJ = 14;

export function apenasDigitos(valor: string): string {
  return valor.replace(/\D/g, '');
}

export function mascararDocumento(valor: string): string {
  const digitos = apenasDigitos(valor).slice(0, DIGITOS_DE_CNPJ);

  if (digitos.length <= DIGITOS_DE_CPF) {
    return mascararCpf(digitos);
  }
  return mascararCnpj(digitos);
}

/** `529.982.247-25` */
export function mascararCpf(valor: string): string {
  const d = apenasDigitos(valor).slice(0, DIGITOS_DE_CPF);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

/** `11.222.333/0001-81` */
export function mascararCnpj(valor: string): string {
  const d = apenasDigitos(valor).slice(0, DIGITOS_DE_CNPJ);
  if (d.length <= 2) return d;
  if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`;
  if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
  if (d.length <= 12) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

/** Quantidade de dígitos compatível com CPF ou CNPJ. */
export function temTamanhoDeDocumento(valor: string): boolean {
  const total = apenasDigitos(valor).length;
  return total === DIGITOS_DE_CPF || total === DIGITOS_DE_CNPJ;
}
