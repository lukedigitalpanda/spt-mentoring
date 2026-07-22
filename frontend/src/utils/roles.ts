import type { User, Role } from '../types';

/**
 * Returns true if the user holds the given role as either their primary or a secondary role.
 */
export function userHasRole(user: User | null | undefined, role: Role): boolean {
  if (!user) return false;
  return user.role === role || (user.secondary_roles ?? []).includes(role);
}
