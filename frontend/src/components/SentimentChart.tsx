import React, { useState, useEffect } from 'react';
import { fetchSentiment } from '../api/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

interface SentimentChartProps {
  subreddit: string;
  startDate: string;
  endDate: string;
}

const SentimentChart: React.FC<SentimentChartProps> = ({ 
  subreddit,
  startDate,
  endDate
}) => {
  const [sentimentData, setSentimentData] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const getSentimentData = async () => {
      if (!subreddit) {
        setLoading(false);
        return;
      }
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchSentiment(subreddit, startDate, endDate);
        setSentimentData(data);
      } catch (err) {
        console.error('Error fetching sentiment data:', err);
        setError('Failed to load sentiment data');
      } finally {
        setLoading(false);
      }
    };

    getSentimentData();
  }, [subreddit, startDate, endDate]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--scale-accent)]"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 text-center py-8 bg-red-50 rounded-lg p-4">
        <div className="mb-2">⚠️ Error</div>
        <div>{error}</div>
      </div>
    );
  }

  if (!subreddit) {
    return (
      <div className="text-center py-8">
        <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
          <h3 className="text-lg font-medium mb-2">No Subreddit Selected</h3>
          <p className="text-[var(--scale-text-secondary)]">
            Please select a subreddit to view sentiment data.
          </p>
        </div>
      </div>
    );
  }

  if (sentimentData.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
          <h3 className="text-lg font-medium mb-2">No Data Available</h3>
          <p className="text-[var(--scale-text-secondary)]">
            No sentiment data is available for r/{subreddit} during this period ({startDate} to {endDate}).
          </p>
        </div>
      </div>
    );
  }

  // Find min and max sentiment values for y-axis configuration
  const sentiments = sentimentData.map(item => item.avg_sentiment);
  const minSentiment = Math.min(...sentiments) - 0.1;
  const maxSentiment = Math.max(...sentiments) + 0.1;

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 shadow-lg rounded border border-[var(--scale-border)]">
          <p className="font-medium">{label}</p>
          <p className="text-sm">
            Sentiment: <span className="font-semibold">{payload[0].value.toFixed(3)}</span>
          </p>
          <p className="text-sm">
            Posts: <span className="font-semibold">{payload[0].payload.post_count}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  // Custom tick formatter for X axis to prevent overcrowding
  const formatXAxis = (value: string) => {
    // Show only some of the dates to avoid overcrowding
    const idx = sentimentData.findIndex(item => item.date === value);
    if (sentimentData.length <= 10 || idx % Math.ceil(sentimentData.length / 10) === 0) {
      return value;
    }
    return '';
  };

  return (
    <div style={{ width: '100%', height: 400 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={sentimentData}
          margin={{ top: 20, right: 30, left: 0, bottom: 25 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
          <XAxis 
            dataKey="date" 
            angle={-45} 
            textAnchor="end" 
            height={60} 
            tickFormatter={formatXAxis}
            stroke="var(--scale-text-light)"
            tick={{ fill: 'var(--scale-text-light)', fontSize: 12 }}
          />
          <YAxis 
            domain={[minSentiment, maxSentiment]}
            tickFormatter={(value) => value.toFixed(2)}
            stroke="var(--scale-text-light)"
            tick={{ fill: 'var(--scale-text-light)', fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line 
            type="monotone" 
            dataKey="avg_sentiment" 
            name="Sentiment"
            stroke="var(--scale-accent)" 
            activeDot={{ r: 6 }} 
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SentimentChart; 