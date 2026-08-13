/**
 * Erro da API no formato Problem Details.
 *
 * Todo erro vindo do backend chega aqui tipado, com `correlation_id` — que é o
 * que o suporte pede quando o usuário relata um problema.
 */
export interface FieldError {
  field: string;
  message: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  correlation_id: string;
  errors: FieldError[];
}

export class ApiError extends Error {
  readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail || problem.title);
    this.name = 'ApiError';
    this.problem = problem;
  }

  get status(): number {
    return this.problem.status;
  }

  /** Último segmento do `type`, ex.: "period-closed". */
  get codigo(): string {
    return this.problem.type.split('/').pop() ?? 'unknown';
  }

  get correlationId(): string {
    return this.problem.correlation_id;
  }

  get erroDeCampo(): Record<string, string> {
    return Object.fromEntries(this.problem.errors.map((e) => [e.field, e.message]));
  }
}

export function problemaGenerico(status: number, detail: string): ProblemDetails {
  return {
    type: 'https://rfbalance/errors/network-error',
    title: 'Falha de comunicação',
    status,
    detail,
    instance: '',
    correlation_id: '',
    errors: [],
  };
}
