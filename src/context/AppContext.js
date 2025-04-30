import React, { createContext, useState, useEffect } from 'react';
import api from '../services/api';

export const AppContext = createContext();

export const AppContextProvider = ({ children }) => {
  const [subreddits, setSubreddits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSubreddit, setSelectedSubreddit] = useState('');
  const [dateRange, setDateRange] = useState({
    startDate: '2023-01-01',
    endDate: '2023-04-01',
  });
  const [timeframe, setTimeframe] = useState('monthly'); // daily, weekly, monthly

  useEffect(() => {
    const fetchSubreddits = async () => {
      setLoading(true);
      try {
        const data = await api.getSubreddits();
        setSubreddits(data);
        if (data.length > 0) {
          setSelectedSubreddit(data[0]);
        }
      } catch (err) {
        setError('Failed to fetch subreddits');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSubreddits();
  }, []);

  const contextValue = {
    subreddits,
    loading,
    error,
    selectedSubreddit,
    setSelectedSubreddit,
    dateRange,
    setDateRange,
    timeframe,
    setTimeframe,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};