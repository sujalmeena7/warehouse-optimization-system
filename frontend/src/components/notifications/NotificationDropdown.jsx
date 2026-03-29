import React, { useEffect, useState } from 'react';
import { X, Check, Trash2 } from 'lucide-react';
import { warehouseApi } from '../../lib/api';
import './NotificationDropdown.css';

const NotificationDropdown = ({ onClose, onNotificationRead }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const response = await warehouseApi.get('/notifications?limit=10');
      setNotifications(response.notifications || []);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (notifId, e) => {
    e.stopPropagation();
    try {
      await warehouseApi.put(`/notifications/${notifId}/read`);
      loadNotifications();
      onNotificationRead?.();
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleDelete = async (notifId, e) => {
    e.stopPropagation();
    try {
      await warehouseApi.delete(`/notifications/${notifId}`);
      loadNotifications();
      onNotificationRead?.();
    } catch (err) {
      console.error('Failed to delete notification:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await warehouseApi.put('/notifications/read-all');
      loadNotifications();
      onNotificationRead?.();
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const getSeverityClass = (severity) => {
    const severityMap = {
      info: 'severity-info',
      warning: 'severity-warning',
      critical: 'severity-critical',
    };
    return severityMap[severity] || 'severity-info';
  };

  const formatTime = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="notification-dropdown">
      <div className="dropdown-header">
        <h3>Notifications</h3>
        <div className="header-actions">
          {notifications.some(n => !n.read) && (
            <button onClick={handleMarkAllRead} className="mark-all-btn" title="Mark all as read">
              Mark all read
            </button>
          )}
          <button onClick={onClose} className="close-btn">
            <X size={16} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="dropdown-body loading">Loading notifications...</div>
      ) : notifications.length === 0 ? (
        <div className="dropdown-body empty">No notifications yet</div>
      ) : (
        <div className="notifications-list">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              className={`notification-item ${!notif.read ? 'unread' : ''} ${getSeverityClass(
                notif.severity
              )}`}
            >
              <div className="notification-content">
                <div className="notification-title">{notif.title}</div>
                <div className="notification-message">{notif.message}</div>
                <div className="notification-time">{formatTime(notif.created_at)}</div>
              </div>
              <div className="notification-actions">
                {!notif.read && (
                  <button
                    onClick={(e) => handleMarkRead(notif.id, e)}
                    className="action-btn mark-read"
                    title="Mark as read"
                  >
                    <Check size={14} />
                  </button>
                )}
                <button
                  onClick={(e) => handleDelete(notif.id, e)}
                  className="action-btn delete"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="dropdown-footer">
        <a href="/notifications" className="view-all-link">
          View all notifications →
        </a>
      </div>
    </div>
  );
};

export default NotificationDropdown;
