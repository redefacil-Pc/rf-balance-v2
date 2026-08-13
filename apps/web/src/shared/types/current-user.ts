/**
 * Usuário autenticado, espelhando `CurrentUserResponse` do backend.
 *
 * Provisório: este tipo será substituído pelo gerado do OpenAPI. Mantido em
 * `snake_case` (ADR-0015) justamente para a troca ser transparente.
 */
export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  roles: string[];
  permissions: string[];
  must_change_password: boolean;
}
