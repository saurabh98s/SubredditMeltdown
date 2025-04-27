import { useState, useEffect } from 'react';
import { fetchKeywords, KeywordData } from '../api/api';

interface KeywordPanelProps {
  subreddit: string;
  timeframe: string;
}

const KeywordPanel: React.FC<KeywordPanelProps> = ({ subreddit, timeframe }) => {
  const [keywords, setKeywords] = useState<KeywordData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchKeywordData = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchKeywords(subreddit, timeframe);
        setKeywords(data);
      } catch (err) {
        setError('Failed to load keyword data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchKeywordData();
  }, [subreddit, timeframe]);

  if (loading) {
    return <div className="py-8 text-center">Loading keyword data...</div>;
  }

  if (error) {
    return <div className="py-8 text-red-500">{error}</div>;
  }

  if (keywords.length === 0) {
    return (
      <div className="py-8 text-center">
        No keyword data available for r/{subreddit} in the selected timeframe.
      </div>
    );
  }

  // Sort keywords by weight
  const sortedKeywords = [...keywords].sort((a, b) => b.weight - a.weight);

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {sortedKeywords.map((keyword, index) => {
          // Calculate size based on weight (normalize between 80% and 160%)
          const minWeight = sortedKeywords[sortedKeywords.length - 1].weight;
          const maxWeight = sortedKeywords[0].weight;
          const range = maxWeight - minWeight;
          const normalizedSize = range === 0 
            ? 100 
            : 80 + Math.round((keyword.weight - minWeight) / range * 80);
          
          // Calculate color intensity based on weight
          const colorIntensity = range === 0 
            ? 500 
            : 300 + Math.round((keyword.weight - minWeight) / range * 500);
          
          // Get appropriate color class based on intensity
          const getColorClass = (intensity: number) => {
            if (intensity <= 300) return 'text-indigo-300';
            if (intensity <= 400) return 'text-indigo-400';
            if (intensity <= 500) return 'text-indigo-500';
            if (intensity <= 600) return 'text-indigo-600';
            if (intensity <= 700) return 'text-indigo-700';
            return 'text-indigo-800';
          };
          
          return (
            <div 
              key={`${keyword.keyword}-${index}`} 
              className="bg-indigo-50 rounded-lg p-3 flex items-center justify-center text-center"
            >
              <span 
                className={`${getColorClass(colorIntensity)} font-medium`}
                style={{ fontSize: `${normalizedSize}%` }}
              >
                {keyword.keyword}
              </span>
            </div>
          );
        })}
      </div>
      
      <div className="mt-4 text-right text-sm text-gray-500">
        <span>Based on {keywords[0]?.post_count || 0} posts</span>
      </div>
    </div>
  );
};

export default KeywordPanel; 