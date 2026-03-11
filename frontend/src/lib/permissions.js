export const canAccessPage = (user, pageKey) => {
  if (!user?.allowed_pages) return false;
  return user.allowed_pages.includes(pageKey);
};

export const canEditInventory = (user) => Boolean(user?.permissions?.can_edit_inventory);
