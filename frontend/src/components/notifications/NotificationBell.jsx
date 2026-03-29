import React, { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { warehouseApi } from '../../lib/api';
import NotificationDropdown from './NotificationDropdown';
import './NotificationBell.css';

const NotificationBell = () => {
  const { user, accessToken } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    if (!user || !accessToken) return;

    // Fetch initial unread count
    loadUnreadCount();

    // Poll for updates every 30 seconds
    const interval = setInterval(loadUnreadCount, 30000);

    return () => clearInterval(interval);
  }, [user, accessToken]);

  const loadUnreadCount = async () => {
    try {
      const response = await warehouseApi.get('/notifications/unread-count');
      setUnreadCount(response.unread || 0);
    } catch (err) {
      // Silently fail, user might not have permission yet
    }
  };

  if (!user) return null;

  return (
    <div className="notification-bell-container">
      <button
        className="notification-bell-button"
        onClick={() => setShowDropdown(!showDropdown)}
        title="Notifications"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {showDropdown && (
        <NotificationDropdown
          onClose={() => setShowDropdown(false)}
          onNotificationRead={() => {
            loadUnreadCount();
          }}
        />
      )}
    </div>
  );
};

export default NotificationBell;
