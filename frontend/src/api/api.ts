import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface SentimentData {
  subreddit: string;
  date: string;
  avg_sentiment: number;
  post_count: number;
}

export interface EventData {
  date: string;
  event: string;
  category: string;
}

export interface KeywordData {
  keyword: string;
  weight: number;
  timeframe: string;
  subreddit: string;
  post_count: number;
}

// API Functions
export const fetchSubreddits = async (): Promise<string[]> => {
  try {
    const response = await api.get<string[]>('/subreddits');
    return response.data;
  } catch (error) {
    console.error('Error fetching subreddits:', error);
    return [];
  }
};

export const fetchSentiment = async (
  subreddit: string,
  startDate: string,
  endDate: string
): Promise<SentimentData[]> => {
  try {
    const response = await api.get<SentimentData[]>('/sentiment', {
      params: { subreddit, start_date: startDate, end_date: endDate },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching sentiment data:', error);
    return [];
  }
};

export const fetchEvents = async (
  startDate: string,
  endDate: string,
  category?: string
): Promise<EventData[]> => {
  try {
    const response = await api.get<EventData[]>('/events', {
      params: { start_date: startDate, end_date: endDate, category },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching events:', error);
    return [];
  }
};

export const fetchKeywords = async (
  subreddit: string,
  timeframe: string
): Promise<KeywordData[]> => {
  try {
    const response = await api.get<KeywordData[]>('/keywords', {
      params: { subreddit, timeframe },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching keywords:', error);
    return [];
  }
};

export default api; 