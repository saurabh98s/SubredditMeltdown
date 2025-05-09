import React, { useState, useEffect } from 'react';
import ReactWordcloud from 'react-wordcloud';
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
  const [keywords, setKeywords] = useState<{ positive: KeywordData[]; negative: KeywordData[] }>({ positive: [], negative: [] });
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

  useEffect(() => {
    setActiveTab(initialActiveTab);
  }, [initialActiveTab]);

  if (loading) {
    return <div className="flex justify-center items-center py-6">Loading keyword data...</div>;
  }

  if (error) {
    return <div className="text-red-500 text-center py-4">{error}</div>;
  }

  const positiveWords = keywords.positive.map((k) => ({ text: k.keyword, value: k.weight }));
  const negativeWords = keywords.negative.map((k) => ({ text: k.keyword, value: k.weight }));

  const words = activeTab === 'positive' ? positiveWords : negativeWords;

  const options = {
    rotations: 2,
    rotationAngles: [-90, 0] as [number, number],
    fontSizes: [15, 60] as [number, number],
    // color scheme based on sentiment
    colors: activeTab === 'positive' ? ['#27ae60'] : ['#e74c3c'],
    enableTooltip: true,
    deterministic: false,
  };

  const callbacks = {
    // optional callbacks
    onWordClick: (word: any) => {
      console.log(`Clicked on word: ${word.text}`);
    }
  };

  return (
    <div>
      {/* Tab Controls */}
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
            Positive
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
            Negative
          </button>
        </div>
      </div>

      {/* Word Cloud */}
      <div style={{ width: '100%', height: `${height}px` }}>
        {words.length > 0 ? (
          <ReactWordcloud
            words={words}
            options={options}
            callbacks={callbacks}
          />
        ) : (
          <div className="text-center text-gray-500 py-6">
            No {activeTab} keywords available for r/{subreddit}.
          </div>
        )}
      </div>

      {/* Footer Text */}
      <div className="mt-4 text-sm text-center text-gray-500">
        Showing the top {words.length} {activeTab} keywords for r/{subreddit}
      </div>
    </div>
  );
};

export default WordCloud;