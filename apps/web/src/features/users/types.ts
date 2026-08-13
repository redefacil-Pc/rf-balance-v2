export interface AccessRole {
  code: string;
  name: string;
  permissions: string[];
}

export interface SystemUser {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  must_change_password: boolean;
  roles: string[];
  last_login_at: string | null;
  /** Nulo quando a pessoa só usa o sistema, sem cadastro operacional. */
  collaborator_id: number | null;
}

export interface UserPage {
  items: SystemUser[];
  next_cursor: string | null;
}

export interface CreatedUser {
  id: number;
  email: string;
  full_name: string;
  roles: string[];
  temporary_password: string;
  collaborator_id: number | null;
}
