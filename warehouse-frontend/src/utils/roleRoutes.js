export const ROLE_HOME = {
  OWNER: '/admin/dashboard',
  MANAGER: '/manager/dashboard',
  INBOUND: '/employee/inbound',
  OUTBOUND: '/employee/outbound',
}

export function homeForRole(role) {
  return ROLE_HOME[role] ?? '/login'
}
