import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  TooltipProps,
} from 'recharts';
import { fetchSentiment, SentimentData } from '../api/api';
import { format, parseISO } from 'date-fns';
import { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent';

interface SentimentChartProps {
  subreddit: string;
  startDate: string;
  endDate: string;
}

interface SentimentDataWithFormat extends SentimentData {
  formattedDate: string;
}

const SentimentChart: React.FC<SentimentChartProps> = ({
  subreddit,
  startDate,
  endDate,
}) => {
  const [sentimentData, setSentimentData] = useState<SentimentData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchSentiment(subreddit, startDate, endDate);
        setSentimentData(data);
      } catch (err) {
        setError('Failed to load sentiment data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [subreddit, startDate, endDate]);

  const formatDate = (dateStr: string) => {
    try {
      return format(parseISO(dateStr), 'MMM d, yyyy');
    } catch (e) {
      return dateStr;
    }
  };

  // Format data for chart
  const chartData = sentimentData.map((item) => ({
    ...item,
    formattedDate: formatDate(item.date),
  }));

  // Custom tooltip
  const CustomTooltip = ({ 
    active, 
    payload, 
    label 
  }: TooltipProps<ValueType, NameType>) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as SentimentDataWithFormat;
      return (
        <div className="bg-white p-4 border border-gray-300 shadow-md rounded-md">
          <p className="font-semibold">{data.formattedDate}</p>
          <p>
            Sentiment: <span className="font-medium">{data.avg_sentiment.toFixed(3)}</span>
          </p>
          <p>
            Posts: <span className="font-medium">{data.post_count}</span>
          </p>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return <div className="flex justify-center py-8">Loading sentiment data...</div>;
  }

  if (error) {
    return <div className="text-red-500 py-8">{error}</div>;
  }

  if (sentimentData.length === 0) {
    return (
      <div className="flex justify-center py-8">
        No sentiment data available for r/{subreddit} in the selected date range.
      </div>
    );
  }

  return (
    <div className="h-96">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="date" 
            tickFormatter={formatDate}
            minTickGap={50}
          />
          <YAxis
            domain={[-1, 1]}
            label={{ 
              value: 'Sentiment Score', 
              angle: -90, 
              position: 'insideLeft',
              style: { textAnchor: 'middle' }
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line
            type="monotone"
            dataKey="avg_sentiment"
            stroke="#8884d8"
            name="Sentiment"
            activeDot={{ r: 8 }}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default SentimentChart; 