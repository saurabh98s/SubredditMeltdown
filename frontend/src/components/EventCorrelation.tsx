import React, { useState, useEffect } from 'react';
import { fetchEventCorrelation } from '../api/api';
import Button from './Button';

interface EventCorrelationProps {
  subreddit: string;
  startDate: string;
  endDate: string;
  contentType?: string;
  onEventSelect?: (eventDate: string) => void;
}

const EventCorrelation: React.FC<EventCorrelationProps> = ({ 
  subreddit, 
  startDate, 
  endDate, 
  contentType = 'submissions',
  onEventSelect
}) => {
  const [correlations, setCorrelations] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showTable, setShowTable] = useState<boolean>(true);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  useEffect(() => {
    const getEventCorrelation = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchEventCorrelation(subreddit, startDate, endDate, contentType);
        setCorrelations(data);
      } catch (err) {
        console.error('Error fetching event correlation:', err);
        setError('Failed to load event correlation data');
      } finally {
        setLoading(false);
      }
    };

    getEventCorrelation();
  }, [subreddit, startDate, endDate, contentType]);

  const handleEventClick = (eventDate: string) => {
    if (onEventSelect) {
      onEventSelect(eventDate);
    }
  };

  const handleCategoryFilter = (category: string) => {
    setActiveCategory(activeCategory === category ? null : category);
  };

  // Get unique categories from correlations
  const categories = correlations
    .map(item => item.event.category?.toLowerCase())
    .filter((category, index, self) => 
      category && self.indexOf(category) === index
    );

  const filteredCorrelations = activeCategory 
    ? correlations.filter(item => 
        item.event.category?.toLowerCase() === activeCategory.toLowerCase()
      )
    : correlations;

  if (loading) {
    return <div className="flex justify-center items-center py-12">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
    </div>;
  }

  if (error) {
    return <div className="py-8 text-center text-red-500">{error}</div>;
  }

  if (correlations.length === 0) {
    return (
      <div className="py-8 text-center">
        <div className="bg-gray-50 p-8 rounded-lg border border-gray-200">
          <h3 className="text-lg font-medium mb-2">No Event Correlations Available</h3>
          <p className="text-gray-600">
            No correlation data is available for this period and subreddit combination.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden">
      <h3 className="text-lg font-medium mb-4">
        Event Impact Analysis for r/{subreddit}
      </h3>
      
      {/* Controls */}
      <div className="flex flex-wrap justify-between items-center gap-3 mb-4">
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <Button
              key={category}
              onClick={() => handleCategoryFilter(category)}
              variant={activeCategory === category ? "primary" : "outline"}
              size="sm"
            >
              {category}
            </Button>
          ))}
          {activeCategory && (
            <Button
              onClick={() => setActiveCategory(null)}
              variant="secondary"
              size="sm"
            >
              Clear Filter
            </Button>
          )}
        </div>
        
        <Button 
          onClick={() => setShowTable(!showTable)}
          variant="outline"
          size="sm"
        >
          {showTable ? 'Show Visualization' : 'Show Table'}
        </Button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 mb-6 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Event</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Impact</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Keywords</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredCorrelations.map((item, index) => (
              <tr 
                key={index} 
                onClick={() => handleEventClick(item.event.date)} 
                className="hover:bg-gray-50 transition-colors cursor-pointer"
              >
                <td className="px-4 py-3 whitespace-nowrap text-sm">{item.event.date}</td>
                <td className="px-4 py-3 text-sm font-medium">{item.event.event}</td>
                <td className="px-4 py-3 text-sm">
                  <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${getCategoryColorClass(item.event.category)}`}>
                    {item.event.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">
                  <div className="flex items-center">
                    <span className={`${getSentimentColor(item.sentiment_change)}`}>
                      {(item.sentiment_change > 0 ? '+' : '') + item.sentiment_change.toFixed(2)}
                    </span>
                    <SentimentArrow value={item.sentiment_change} />
                  </div>
                </td>
                <td className="px-4 py-3 text-sm">
                  <div className="flex flex-wrap gap-1">
                    {item.related_keywords.map((keyword: string, i: number) => (
                      <span key={i} className="inline-block px-2 py-0.5 text-xs bg-blue-50 text-blue-700 rounded-full">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="font-medium text-gray-900 text-base mb-2">About Event Impact Analysis</h3>
        <p className="text-gray-600 text-sm">
          This analysis shows how key events correlate with changes in sentiment across r/{subreddit}. 
          A positive impact score indicates a positive shift in sentiment following the event, while a negative score 
          indicates a decrease in sentiment.
        </p>
        <p className="text-gray-600 text-sm mt-2">
          Click on any event row to view conversations from that date.
        </p>
      </div>
    </div>
  );
};

// Helper components
const SentimentArrow: React.FC<{ value: number }> = ({ value }) => {
  if (Math.abs(value) < 0.05) return null;
  
  return value > 0 
    ? <svg className="h-5 w-5 ml-1 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd"></path></svg>
    : <svg className="h-5 w-5 ml-1 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd"></path></svg>;
};

// Helper functions
const getCategoryColorClass = (category: string): string => {
  const categories: { [key: string]: string } = {
    'politics': 'bg-blue-100 text-blue-800',
    'platform': 'bg-purple-100 text-purple-800',
    'technology': 'bg-green-100 text-green-800',
    'gaming': 'bg-orange-100 text-orange-800',
    'economic': 'bg-yellow-100 text-yellow-800',
    'community': 'bg-indigo-100 text-indigo-800',
    'news': 'bg-cyan-100 text-cyan-800',
    'entertainment': 'bg-pink-100 text-pink-800',
    'sports': 'bg-lime-100 text-lime-800',
    'pandemic': 'bg-amber-100 text-amber-800',
  };
  
  return categories[category?.toLowerCase()] || 'bg-gray-100 text-gray-800';
};

const getSentimentColor = (value: number): string => {
  if (value > 0.1) return 'text-green-600 font-semibold';
  if (value < -0.1) return 'text-red-600 font-semibold';
  return 'text-gray-600';
};

export default EventCorrelation; 