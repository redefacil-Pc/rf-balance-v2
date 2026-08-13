/**
 * Leitura de cookie não-HttpOnly.
 *
 * Só serve para o token CSRF, que é legível por design (ADR-0003). O cookie de
 * sessão é HttpOnly e não pode — nem deve — ser lido daqui.
 */
export function lerCookie(nome: string): string | null {
  const alvo = `${encodeURIComponent(nome)}=`;
  const encontrado = document.cookie
    .split('; ')
    .find((parte) => parte.startsWith(alvo));

  return encontrado ? decodeURIComponent(encontrado.slice(alvo.length)) : null;
}
