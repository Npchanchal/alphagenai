/** Platform super is these operator logins. The server refuses the role for every other email. */
export const PLATFORM_SUPER_EMAILS = new Set([
  "dk@citealpha.com",
  "admin.team@citealpha.com",
]);

export function isPlatformSuper(
  user: { email?: string | null; platform_admin_role?: string | null } | null | undefined,
): boolean {
  if (!user || user.platform_admin_role !== "super") return false;
  return PLATFORM_SUPER_EMAILS.has((user.email || "").trim().toLowerCase());
}
