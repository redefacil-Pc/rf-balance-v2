import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * Filtros vivem nos search params da URL, não em `useState`.
 *
 * A tela precisa ser compartilhável e sobreviver ao recarregamento — um gestor
 * manda "olha esse filtro aqui" e o link tem que abrir a mesma coisa.
 */
export function useFiltrosNaUrl<T extends object>(
  converter: (params: URLSearchParams) => T,
): [T, (novos: T) => void] {
  const [params, setParams] = useSearchParams();

  const filtros = useMemo(() => converter(params), [params, converter]);

  const aplicar = useCallback(
    (novos: T) => {
      const proximos = new URLSearchParams();
      for (const [chave, valor] of Object.entries(novos as Record<string, unknown>)) {
        if (valor !== undefined && valor !== null && valor !== '') {
          proximos.set(chave, String(valor));
        }
      }
      setParams(proximos, { replace: true });
    },
    [setParams],
  );

  return [filtros, aplicar];
}
