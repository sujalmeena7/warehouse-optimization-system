// Role-based permissions matching backend ROLE_PERMISSIONS
const ROLE_PERMISSIONS = {
  Admin: {
    dashboard: true,
    inventory: true,
    orders: true,
    routes: true,
    layout: true,
    analytics: true,
    alerts: true,
    can_edit_inventory: true,
  },
  Manager: {
    dashboard: true,
    inventory: true,
    orders: true,
    routes: true,
    layout: true,
    analytics: true,
    alerts: true,
    can_edit_inventory: true,
  },
  Staff: {
    dashboard: true,
    inventory: true,
    orders: true,
    routes: true,
    layout: true,
    analytics: false,
    alerts: true,
    can_edit_inventory: false,
  },
};

export const canAccessPage = (user, pageKey) => {
  if (!user?.role) return false;
  // Support both JWT login (role-based) and demo login (allowed_pages)
  if (user.allowed_pages) {
    return user.allowed_pages.includes(pageKey);
  }
  const perms = ROLE_PERMISSIONS[user.role];
  return perms ? !!perms[pageKey] : false;
};

export const canEditInventory = (user) => {
  if (!user?.role) return false;
  if (user.permissions) return Boolean(user.permissions.can_edit_inventory);
  const perms = ROLE_PERMISSIONS[user.role];
  return perms ? !!perms.can_edit_inventory : false;
};
