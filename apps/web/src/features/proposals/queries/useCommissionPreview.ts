import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { requisitar } from '@/shared/api/http-client';
import type { ApiError } from '@/shared/api/problem-details';

export interface CommissionPreview {
  company_commission_amount: string;
  consultant_commission_amount: string | null;
  strategy: string | null;
  estimate: boolean;
  note: string | null;
}

interface Entrada {
  consultant_id?: number;
  business_date: string;
  /** string decimal já convertida pelo schema, não o valor mascarado */
  operation_amount: string;
  tps_percentage: string;
}

/** Espera o operador parar de digitar antes de perguntar ao servidor. */
function useDebounce<T>(valor: T, ms: number): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const id = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(id);
  }, [valor, ms]);
  return atrasado;
}

export function useCommissionPreview(entrada: Entrada) {
  const chave = useDebounce(JSON.stringify(entrada), 400);
  const completa =
    entrada.consultant_id !== undefined &&
    entrada.business_date !== '' &&
    Number(entrada.operation_amount) > 0 &&
    entrada.tps_percentage !== '';

  return useQuery<CommissionPreview, ApiError>({
    queryKey: ['commission-preview', chave],
    queryFn: ({ signal }) =>
      requisitar('/commission-preview', {
        method: 'POST',
        body: JSON.parse(chave) as Entrada,
        signal,
      }),
    enabled: completa,
    // a prévia é derivada do que está na tela; não vale reaproveitar entre aberturas
    gcTime: 0,
    retry: false,
  });
}
