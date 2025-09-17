import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// Configure axios defaults
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

function App() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newUser, setNewUser] = useState({ name: '', email: '' });
  const [apiStatus, setApiStatus] = useState(null);

  // Check API health on component mount
  useEffect(() => {
    checkApiHealth();
  }, []);

  const checkApiHealth = async () => {
    try {
      const response = await api.get('/health');
      setApiStatus(response.data);
    } catch (err) {
      setApiStatus({ status: 'error', message: 'API unavailable' });
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/users');
      setUsers(response.data.data || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch users');
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
    }
  };

  const createUser = async (e) => {
    e.preventDefault();
    
    if (!newUser.name.trim() || !newUser.email.trim()) {
      setError('Name and email are required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.post('/users', newUser);
      setNewUser({ name: '', email: '' });
      // Refresh users list
      await fetchUsers();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create user');
      console.error('Error creating user:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewUser(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Microservices Frontend</h1>
        
        {/* API Status */}
        <div className={`status-indicator ${apiStatus?.status}`}>
          <h3>API Status: {apiStatus?.status || 'Checking...'}</h3>
          {apiStatus?.service && (
            <p>Service: {apiStatus.service} | Database: {apiStatus.database}</p>
          )}
          {apiStatus?.timestamp && (
            <p>Last checked: {new Date(apiStatus.timestamp).toLocaleString()}</p>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
          </div>
        )}

        {/* User Creation Form */}
        <div className="user-form">
          <h2>Add New User</h2>
          <form onSubmit={createUser}>
            <div className="form-group">
              <input
                type="text"
                name="name"
                placeholder="Full Name"
                value={newUser.name}
                onChange={handleInputChange}
                disabled={loading}
                required
              />
            </div>
            <div className="form-group">
              <input
                type="email"
                name="email"
                placeholder="Email Address"
                value={newUser.email}
                onChange={handleInputChange}
                disabled={loading}
                required
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? 'Creating...' : 'Create User'}
            </button>
          </form>
        </div>

        {/* Users Section */}
        <div className="users-section">
          <div className="users-header">
            <h2>Users ({users.length})</h2>
            <button 
              onClick={fetchUsers} 
              disabled={loading}
              className="refresh-button"
            >
              {loading ? 'Loading...' : 'Refresh Users'}
            </button>
          </div>

          {users.length > 0 ? (
            <div className="users-grid">
              {users.map(user => (
                <div key={user.id} className="user-card">
                  <h3>{user.name}</h3>
                  <p>{user.email}</p>
                  <small>
                    Created: {new Date(user.created_at).toLocaleDateString()}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-users">
              <p>No users found. Click "Refresh Users" to load data or create a new user.</p>
            </div>
          )}
        </div>

        {/* System Info */}
        <div className="system-info">
          <h3>System Information</h3>
          <p>Environment: {process.env.NODE_ENV}</p>
          <p>API URL: {API_BASE_URL}</p>
          <p>Build Time: {process.env.REACT_APP_BUILD_TIME || 'Not set'}</p>
        </div>
      </header>
    </div>
  );
}

export default App;
