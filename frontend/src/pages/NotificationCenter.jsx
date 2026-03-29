import React, { useEffect, useState } from 'react';
import { Check, Trash2, Archive } from 'lucide-react';
import { warehouseApi } from '@/lib/api';
import './NotificationCenter.css';

const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all'); // all, unread, read
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);

  const NOTIFICATIONS_PER_PAGE = 20;

  useEffect(() => {
    loadNotifications();
  }, [filter, page]);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const response = await warehouseApi.get(
        `/notifications?limit=${NOTIFICATIONS_PER_PAGE}&skip=${page * NOTIFICATIONS_PER_PAGE}`
      );

      let filtered = response.notifications || [];
      if (filter === 'unread') {
        filtered = filtered.filter(n => !n.read);
      } else if (filter === 'read') {
        filtered = filtered.filter(n => n.read);
      }

      setNotifications(filtered);
      setTotal(response.total || 0);
      setUnreadCount(response.unread || 0);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (notifId) => {
    try {
      await warehouseApi.put(`/notifications/${notifId}/read`);
      loadNotifications();
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await warehouseApi.put('/notifications/read-all');
      loadNotifications();
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const handleDelete = async (notifId) => {
    try {
      await warehouseApi.delete(`/notifications/${notifId}`);
      loadNotifications();
    } catch (err) {
      console.error('Failed to delete notification:', err);
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      info: '#0066cc',
      warning: '#ff9900',
      critical: '#cc0000',
    };
    return colors[severity] || '#0066cc';
  };

  const formatTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const totalPages = Math.ceil(total / NOTIFICATIONS_PER_PAGE);

  return (
    <div className="notification-center">
      <div className="nc-header">
        <div>
          <h1>Notifications</h1>
          <p className="subtitle">{unreadCount} unread notifications</p>
        </div>
        {unreadCount > 0 && (
          <button onClick={handleMarkAllRead} className="mark-all-button">
            Mark all as read
          </button>
        )}
      </div>

      <div className="nc-filters">
        <button
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => {
            setFilter('all');
            setPage(0);
          }}
        >
          All
        </button>
        <button
          className={`filter-btn ${filter === 'unread' ? 'active' : ''}`}
          onClick={() => {
            setFilter('unread');
            setPage(0);
          }}
        >
          Unread ({unreadCount})
        </button>
        <button
          className={`filter-btn ${filter === 'read' ? 'active' : ''}`}
          onClick={() => {
            setFilter('read');
            setPage(0);
          }}
        >
          Read
        </button>
      </div>

      {loading ? (
        <div className="nc-loading">Loading notifications...</div>
      ) : notifications.length === 0 ? (
        <div className="nc-empty">
          {filter === 'unread' ? 'No unread notifications' : 'No notifications'}
        </div>
      ) : (
        <>
          <div className="nc-list">
            {notifications.map((notif) => (
              <div
                key={notif.id}
                className={`nc-item ${!notif.read ? 'unread' : ''}`}
                style={{ borderLeftColor: getSeverityColor(notif.severity) }}
              >
                <div className="nc-item-content">
                  <div className="nc-item-header">
                    <h3>{notif.title}</h3>
                    <span className="nc-item-time">{formatTime(notif.created_at)}</span>
                  </div>
                  <p className="nc-item-message">{notif.message}</p>
                  {notif.action_url && (
                    <a href={notif.action_url} className="nc-item-action">
                      View related item →
                    </a>
                  )}
                </div>
                <div className="nc-item-actions">
                  {!notif.read && (
                    <button
                      onClick={() => handleMarkRead(notif.id)}
                      className="nc-action-btn mark-read"
                      title="Mark as read"
                    >
                      <Check size={16} />
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(notif.id)}
                    className="nc-action-btn delete"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="nc-pagination">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
              >
                Previous
              </button>
              <span>
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page === totalPages - 1}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default NotificationCenter;
