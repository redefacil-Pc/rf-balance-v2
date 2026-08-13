/**
 * Máscara da chave PIX, que muda conforme o tipo escolhido.
 *
 * CPF, CNPJ e telefone têm formato conhecido e ganham máscara. E-mail e chave
 * aleatória não têm — e aplicar máscara neles corromperia a chave, que é
 * justamente o dado usado para pagar alguém.
 */

import { mascararCnpj, mascararCpf } from '@/shared/formatters/document-mask';
import { mascararTelefone } from '@/shared/formatters/phone-mask';

export type TipoDeChavePix = 'CPF' | 'CNPJ' | 'EMAIL' | 'TELEFONE' | 'ALEATORIA';

export function mascararChavePix(tipo: TipoDeChavePix | undefined) {
  return (valor: string): string => {
    switch (tipo) {
      case 'CPF':
        return mascararCpf(valor);
      case 'CNPJ':
        return mascararCnpj(valor);
      case 'TELEFONE':
        return mascararTelefone(valor);
      default:
        return valor;
    }
  };
}

export function placeholderDaChavePix(tipo: TipoDeChavePix | undefined): string {
  switch (tipo) {
    case 'CPF':
      return '000.000.000-00';
    case 'CNPJ':
      return '00.000.000/0000-00';
    case 'TELEFONE':
      return '(00) 00000-0000';
    case 'EMAIL':
      return 'nome@dominio.com';
    case 'ALEATORIA':
      return 'chave aleatória do banco';
    default:
      return 'Escolha o tipo primeiro';
  }
}
