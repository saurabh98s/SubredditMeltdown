import React, { useState, useEffect } from 'react';
import { fetchNegativeTrendDrivers } from '../api/api';

interface NegativeTrendAnalysisProps {
  subreddit: string;
  startDate: string;
  endDate: string;
  contentType?: string;
}

const NegativeTrendAnalysis: React.FC<NegativeTrendAnalysisProps> = ({
  subreddit,
  startDate,
  endDate,
  contentType = 'submissions'
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [trendData, setTrendData] = useState<any>(null);

  useEffect(() => {
    const loadNegativeTrendData = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchNegativeTrendDrivers(subreddit, startDate, endDate, contentType);
        setTrendData(data);
      } catch (err) {
        console.error('Error loading negative trend data:', err);
        setError('Failed to load negative trend data');
      } finally {
        setLoading(false);
      }
    };

    loadNegativeTrendData();
  }, [subreddit, startDate, endDate, contentType]);

  if (loading) {
    return <div className="py-8 text-center">Analyzing sentiment trends...</div>;
  }

  if (error) {
    return <div className="py-8 text-center text-red-500">{error}</div>;
  }

  if (!trendData || trendData.trend === 'neutral' || trendData.conversations.length === 0) {
    return (
      <div className="py-8 text-center">
        <div className="bg-blue-50 p-6 rounded-lg mb-6">
          <h3 className="text-xl font-medium text-blue-800 mb-2">No Significant Negative Trends</h3>
          <p className="text-blue-600">
            No significant negative sentiment trends were detected in r/{subreddit} during the selected period.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Trend Summary */}
      <div className="bg-red-50 p-6 rounded-lg mb-6">
        <h3 className="text-xl font-medium text-red-800 mb-2">Negative Trend Detected</h3>
        <p className="text-red-600 mb-4">
          A significant drop in sentiment was detected on <strong>{trendData.trend_date}</strong>.
        </p>
        <div className="grid grid-cols-3 gap-4 mt-3">
          <div className="bg-white p-3 rounded shadow-sm">
            <div className="text-sm text-gray-500">Previous Sentiment</div>
            <div className="text-xl font-semibold text-gray-800">
              {trendData.prev_sentiment.toFixed(3)}
            </div>
          </div>
          <div className="bg-white p-3 rounded shadow-sm">
            <div className="text-sm text-gray-500">Current Sentiment</div>
            <div className="text-xl font-semibold text-red-600">
              {trendData.current_sentiment.toFixed(3)}
            </div>
          </div>
          <div className="bg-white p-3 rounded shadow-sm">
            <div className="text-sm text-gray-500">Sentiment Drop</div>
            <div className="text-xl font-semibold text-red-800">
              {trendData.sentiment_change.toFixed(3)}
            </div>
          </div>
        </div>
      </div>

      {/* Content that drove the negative trend */}
      <h3 className="text-lg font-medium text-gray-800 mb-4">
        Content That Drove This Negative Trend
      </h3>

      <div className="space-y-4">
        {trendData.conversations.map((item: any, index: number) => (
          <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 flex justify-between items-center">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-gray-700">{item.author || '[deleted]'}</span>
                <span className="text-xs text-gray-500">on {item.date}</span>
              </div>
              <div className="flex items-center space-x-3">
                <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">
                  Sentiment: {item.sentiment.toFixed(2)}
                </span>
                <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                  Score: {item.score}
                </span>
              </div>
            </div>
            <div className="p-4">
              {item.title && (
                <h4 className="font-medium text-gray-900 mb-2">{item.title}</h4>
              )}
              <div className="text-gray-600 text-sm whitespace-pre-line">
                {item.content}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-gray-100 rounded-lg">
        <h3 className="font-semibold text-gray-800 text-lg mb-2">Understanding Negative Trends</h3>
        <p className="text-gray-600 text-sm">
          The content shown above had the most significant negative sentiment scores during the 
          detected negative trend. These posts and comments reflect the topics and concerns that 
          likely contributed to the overall sentiment decrease in r/{subreddit}.
        </p>
      </div>
    </div>
  );
};

export default NegativeTrendAnalysis; 