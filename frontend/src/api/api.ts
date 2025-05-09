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
  impact_score?: number;
}

export interface KeywordData {
  keyword: string;
  weight: number;
  timeframe: string;
  subreddit: string;
  post_count: number;
}

export interface EventCorrelationData {
  event: EventData;
  sentiment_before: number;
  sentiment_after: number;
  sentiment_change: number;
  related_keywords: string[];
  conversation_samples: string[];
}

export interface SentimentTimeseriesData {
  date: string;
  avg_sentiment: number;
  post_count: number;
  events: EventData[];
}

export interface ConversationData {
  id: string;
  date: string;
  title?: string;
  content: string;
  url?: string;
  author: string;
  score: number;
  sentiment: number;
  days_from_event: number;
  type: 'submission' | 'comment';
}

export interface ConversationsResponse {
  event: {
    date: string;
    name: string;
    category: string;
  };
  conversations: ConversationData[];
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
  endDate: string,
  contentType: string = 'submissions'
): Promise<SentimentData[]> => {
  try {
    const response = await api.get<SentimentData[]>('/sentiment', {
      params: { 
        subreddit, 
        start_date: startDate, 
        end_date: endDate,
        content_type: contentType
      },
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

export const fetchEventCorrelation = async (
  subreddit: string,
  startDate: string,
  endDate: string,
  contentType: string = 'submissions'
): Promise<EventCorrelationData[]> => {
  try {
    const response = await api.get<EventCorrelationData[]>('/events/correlation', {
      params: {
        subreddit,
        start_date: startDate,
        end_date: endDate,
        content_type: contentType
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching event correlation:', error);
    return [];
  }
};

export const fetchSentimentTimeseries = async (
  subreddit: string,
  startDate: string,
  endDate: string,
  contentType: string = 'submissions',
  includeEvents: boolean = true
): Promise<SentimentTimeseriesData[]> => {
  try {
    const response = await api.get<SentimentTimeseriesData[]>('/sentiment/timeseries', {
      params: {
        subreddit,
        start_date: startDate,
        end_date: endDate,
        content_type: contentType,
        include_events: includeEvents
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching sentiment timeseries:', error);
    return [];
  }
};

export const fetchConversations = async (
  subreddit: string,
  eventDate: string,
  windowDays: number = 3,
  limit: number = 20
): Promise<ConversationsResponse> => {
  try {
    const response = await api.get<ConversationsResponse>('/conversations', {
      params: {
        subreddit,
        event_date: eventDate,
        window_days: windowDays,
        limit
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching conversations:', error);
    return {
      event: {
        date: eventDate,
        name: 'Error loading event',
        category: 'unknown'
      },
      conversations: []
    };
  }
};

export const fetchGeneratedEvents = async (
  subreddit: string,
  startDate: string,
  endDate: string,
  contentType: string = 'submissions',
  minSentimentChange: number = 0.1
): Promise<EventData[]> => {
  try {
    const response = await api.get<EventData[]>('/events/generate', {
      params: { 
        subreddit,
        start_date: startDate, 
        end_date: endDate,
        content_type: contentType,
        min_sentiment_change: minSentimentChange
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching generated events:', error);
    return [];
  }
};

export default api; 