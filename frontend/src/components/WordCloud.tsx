import React, { useState, useEffect } from 'react';
import { fetchSentimentKeywords, KeywordData } from '../api/api';

interface WordCloudProps {
  subreddit: string;
  timeframe?: string;
  width?: number;
  height?: number;
  initialActiveTab?: 'positive' | 'negative';
}

const WordCloud: React.FC<WordCloudProps> = ({
  subreddit,
  timeframe = 'weekly',
  width = 700,
  height = 400,
  initialActiveTab = 'positive'
}) => {
  const [keywords, setKeywords] = useState<{ positive: KeywordData[]; negative: KeywordData[] }>({
    positive: [],
    negative: []
  });
  const [activeTab, setActiveTab] = useState<'positive' | 'negative'>(initialActiveTab);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadKeywords = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchSentimentKeywords(subreddit, timeframe);
        setKeywords(data);
      } catch (err) {
        console.error('Error loading sentiment keywords:', err);
        setError('Failed to load keyword data');
      } finally {
        setLoading(false);
      }
    };

    loadKeywords();
  }, [subreddit, timeframe]);

  // Update active tab when initialActiveTab prop changes
  useEffect(() => {
    setActiveTab(initialActiveTab);
  }, [initialActiveTab]);

  if (loading) {
    return <div className="flex justify-center items-center py-6">Loading keyword data...</div>;
  }

  if (error) {
    return <div className="text-red-500 text-center py-4">{error}</div>;
  }

  if (!keywords.positive.length && !keywords.negative.length) {
    return (
      <div className="text-center py-4">
        No keyword data available for r/{subreddit}.
      </div>
    );
  }
  
  // Get the keywords for the active tab
  const displayKeywords = keywords[activeTab] || [];
  
  // Sort keywords by weight (descending)
  const sortedKeywords = [...displayKeywords].sort((a, b) => b.weight - a.weight);
  
  return (
    <div>
      <div className="flex justify-center mb-4">
        <div className="inline-flex rounded-md shadow-sm" role="group">
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium rounded-l-lg ${
              activeTab === 'positive'
                ? 'bg-green-600 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-800 border border-gray-200'
            }`}
            onClick={() => setActiveTab('positive')}
          >
            Positive Keywords
          </button>
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium rounded-r-lg ${
              activeTab === 'negative'
                ? 'bg-red-600 text-white'
                : 'bg-white hover:bg-gray-100 text-gray-800 border border-gray-200'
            }`}
            onClick={() => setActiveTab('negative')}
          >
            Negative Keywords
          </button>
        </div>
      </div>

      <div className="flex flex-wrap justify-center items-center gap-2 p-4" style={{ minHeight: `${height}px`, width: `${width}px`, maxWidth: '100%', margin: '0 auto' }}>
        {sortedKeywords.map((keyword, index) => {
          // Calculate size based on weight (normalize between 100% and 200%)
          const minWeight = sortedKeywords[sortedKeywords.length - 1]?.weight || 1;
          const maxWeight = sortedKeywords[0]?.weight || 100;
          const range = maxWeight - minWeight;
          const normalizedSize = range === 0 
            ? 100 
            : 100 + Math.round((keyword.weight - minWeight) / range * 100);
          
          // Calculate opacity based on weight
          const opacity = range === 0 
            ? 0.7 
            : 0.5 + ((keyword.weight - minWeight) / range * 0.5);
            
          // Get appropriate color based on sentiment and tab
          const getColor = () => {
            if (activeTab === 'positive') {
              return 'rgb(39, 174, 96)';
            } else {
              return 'rgb(231, 76, 60)';
            }
          };
          
          return (
            <div 
              key={`${keyword.keyword}-${index}`}
              className="inline-block m-1 px-3 py-2 rounded-lg hover:shadow-md transition-all duration-200 cursor-default"
              style={{
                fontSize: `${normalizedSize}%`,
                color: getColor(),
                opacity: opacity,
                fontWeight: normalizedSize > 150 ? 'bold' : 'normal',
                transform: `rotate(${(index % 5) - 2}deg)`
              }}
              title={`${keyword.keyword}: weight ${keyword.weight.toFixed(2)}`}
            >
              {keyword.keyword}
            </div>
          );
        })}
        
        {!sortedKeywords.length && (
          <div className="text-gray-500">
            No {activeTab} keywords available for visualization.
          </div>
        )}
      </div>

      <div className="mt-4 text-sm text-center text-gray-500">
        Showing the top {sortedKeywords.length} {activeTab} keywords for r/{subreddit}
      </div>
    </div>
  );
};

export default WordCloud; 