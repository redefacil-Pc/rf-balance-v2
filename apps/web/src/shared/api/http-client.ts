import { CSRF_COOKIE, CSRF_HEADER } from '@/shared/api/constants';
import { ApiError, problemaGenerico, type ProblemDetails } from '@/shared/api/problem-details';
import { lerCookie } from '@/shared/lib/cookie';

/**
 * Cliente HTTP da aplicação.
 *
 * Responsabilidades: enviar o cookie de sessão, reenviar o token CSRF no header,
 * converter erro em `ApiError` e tentar **uma** renovação de sessão ao receber
 * 401. Quando o client gerado do OpenAPI entrar, ele passa a usar este fetch
 * como transporte, sem duplicar essas regras.
 */
const BASE = '/api/v1';
// Nestes caminhos um 401 é resposta legítima, não sessão a renovar: tentar
// renovar aqui causaria laço.
const SEM_RENOVACAO = ['/auth/login', '/auth/refresh', '/auth/logout'];

interface Opcoes {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Comando financeiro reenviado precisa repetir a mesma chave. */
  idempotencyKey?: string;
  signal?: AbortSignal;
}

export async function requisitar<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  const resposta = await enviar(caminho, opcoes);

  if (resposta.status === 401 && !SEM_RENOVACAO.includes(caminho)) {
    const renovou = await tentarRenovar();
    if (renovou) {
      return interpretar<T>(await enviar(caminho, opcoes));
    }
  }

  return interpretar<T>(resposta);
}

async function enviar(caminho: string, opcoes: Opcoes): Promise<Response> {
  const metodo = opcoes.method ?? 'GET';
  const headers: Record<string, string> = { Accept: 'application/json' };
  // `FormData` define o próprio Content-Type com boundary; o browser cuida disso.
  const ehFormData = opcoes.body instanceof FormData;

  if (opcoes.body !== undefined && !ehFormData) {
    headers['Content-Type'] = 'application/json';
  }
  if (metodo !== 'GET') {
    const csrf = lerCookie(CSRF_COOKIE);
    if (csrf) {
      headers[CSRF_HEADER] = csrf;
    }
  }
  if (opcoes.idempotencyKey) {
    headers['Idempotency-Key'] = opcoes.idempotencyKey;
  }

  try {
    return await fetch(BASE + caminho, {
      method: metodo,
      headers,
      // sessão em cookie HttpOnly: sem isto o navegador não envia (ADR-0003)
      credentials: 'include',
      body:
        opcoes.body === undefined
          ? undefined
          : ehFormData
            ? (opcoes.body as FormData)
            : JSON.stringify(opcoes.body),
      signal: opcoes.signal,
    });
  } catch (causa) {
    throw new ApiError(
      problemaGenerico(0, causa instanceof Error ? causa.message : 'Sem conexão com o servidor.'),
    );
  }
}

async function tentarRenovar(): Promise<boolean> {
  const csrf = lerCookie(CSRF_COOKIE);
  if (!csrf) {
    return false;
  }
  try {
    const resposta = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { [CSRF_HEADER]: csrf },
      credentials: 'include',
    });
    return resposta.ok;
  } catch {
    return false;
  }
}

async function interpretar<T>(resposta: Response): Promise<T> {
  if (resposta.status === 204) {
    return undefined as T;
  }

  const texto = await resposta.text();

  if (!resposta.ok) {
    throw new ApiError(extrairProblema(resposta, texto));
  }

  return texto ? (JSON.parse(texto) as T) : (undefined as T);
}

function extrairProblema(resposta: Response, texto: string): ProblemDetails {
  try {
    const dados = JSON.parse(texto) as Partial<ProblemDetails>;
    if (dados.type && dados.status) {
      return { errors: [], ...dados } as ProblemDetails;
    }
  } catch {
    // corpo não era JSON: cai no problema genérico
  }
  return problemaGenerico(resposta.status, resposta.statusText || 'Erro inesperado.');
}
