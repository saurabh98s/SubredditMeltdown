import axios from 'axios';

// Base API URL - replace with your actual API url when ready
const API_URL = 'http://localhost:8000';

// Mock data for development
const mockSubreddits = ['depression', 'anxiety', 'mentalhealth', 'bipolar', 'ptsd'];

const mockSentimentData = (subreddit, startDate, endDate) => {
  const dates = [];
  const currentDate = new Date(startDate);
  const end = new Date(endDate);
  
  while (currentDate <= end) {
    dates.push(new Date(currentDate));
    currentDate.setDate(currentDate.getDate() + 1);
  }
  
  return dates.map(date => ({
    subreddit,
    date: date.toISOString().split('T')[0],
    sentiment_score: Math.random() * 2 - 1 // Random score between -1 and 1
  }));
};

const mockEvents = (startDate, endDate, category = null) => {
  const events = [
    { date: '2023-01-15', event: 'Global Economic Forum', category: 'economic' },
    { date: '2023-01-25', event: 'Winter Storm Warning', category: 'weather' },
    { date: '2023-02-10', event: 'Major Tech Layoffs', category: 'economic' },
    { date: '2023-02-28', event: 'Mental Health Awareness Month', category: 'health' },
    { date: '2023-03-15', event: 'Spring Break Begins', category: 'education' },
  ];
  
  return category 
    ? events.filter(event => event.category === category)
    : events;
};

const mockKeywords = (subreddit, timeframe) => {
  const keywords = {
    depression: [
      { keyword: 'therapy', weight: 0.85, timeframe, subreddit },
      { keyword: 'medication', weight: 0.75, timeframe, subreddit },
      { keyword: 'isolation', weight: 0.65, timeframe, subreddit },
      { keyword: 'insomnia', weight: 0.60, timeframe, subreddit },
      { keyword: 'hopeless', weight: 0.55, timeframe, subreddit },
    ],
    anxiety: [
      { keyword: 'panic', weight: 0.90, timeframe, subreddit },
      { keyword: 'worry', weight: 0.85, timeframe, subreddit },
      { keyword: 'stress', weight: 0.80, timeframe, subreddit },
      { keyword: 'overwhelmed', weight: 0.70, timeframe, subreddit },
      { keyword: 'fear', weight: 0.65, timeframe, subreddit },
    ],
    mentalhealth: [
      { keyword: 'support', weight: 0.85, timeframe, subreddit },
      { keyword: 'resources', weight: 0.75, timeframe, subreddit },
      { keyword: 'recovery', weight: 0.70, timeframe, subreddit },
      { keyword: 'stigma', weight: 0.65, timeframe, subreddit },
      { keyword: 'awareness', weight: 0.60, timeframe, subreddit },
    ]
  };
  
  return keywords[subreddit] || [];
};

// API service
const api = {
  getSubreddits: async () => {
    try {
      // When ready to connect to real API:
      // const response = await axios.get(`${API_URL}/subreddits`);
      // return response.data;
      
      // Using mock data for now
      return mockSubreddits;
    } catch (error) {
      console.error('Error fetching subreddits:', error);
      throw error;
    }
  },
  
  getSentiment: async (subreddit, startDate, endDate) => {
    try {
      // When ready to connect to real API:
      // const response = await axios.get(`${API_URL}/sentiment`, {
      //   params: { subreddit, start_date: startDate, end_date: endDate }
      // });
      // return response.data;
      
      // Using mock data for now
      return mockSentimentData(subreddit, startDate, endDate);
    } catch (error) {
      console.error('Error fetching sentiment data:', error);
      throw error;
    }
  },
  
  getEvents: async (startDate, endDate, category = null) => {
    try {
      // When ready to connect to real API:
      // const response = await axios.get(`${API_URL}/events`, {
      //   params: { start_date: startDate, end_date: endDate, category }
      // });
      // return response.data;
      
      // Using mock data for now
      return mockEvents(startDate, endDate, category);
    } catch (error) {
      console.error('Error fetching events:', error);
      throw error;
    }
  },
  
  getKeywords: async (subreddit, timeframe) => {
    try {
      // When ready to connect to real API:
      // const response = await axios.get(`${API_URL}/keywords`, {
      //   params: { subreddit, timeframe }
      // });
      // return response.data;
      
      // Using mock data for now
      return mockKeywords(subreddit, timeframe);
    } catch (error) {
      console.error('Error fetching keywords:', error);
      throw error;
    }
  }
};

export default api;