import React, { useState, useEffect } from 'react';
import { fetchSentimentTimeseries, fetchSentiment, fetchEvents, fetchSentimentKeywords } from '../api/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Scatter,
  ReferenceArea,
} from 'recharts';
import Button from './Button';

interface SentimentTimeseriesProps {
  subreddit: string;
  startDate: string;
  endDate: string;
  contentType?: string;
  onEventSelect?: (eventDate: string) => void;
  initialViewMode?: 'chart' | 'table';
  showVisualization?: boolean;
}

interface TimeseriesData {
  date: string;
  sentiment: number;
  count: number;
  events?: any[];
}

interface Event {
  date: string;
  event: string;
  category: string;
  impact_score?: number;
}

interface TopWordData {
  positive: { keyword: string; weight: number }[];
  negative: { keyword: string; weight: number }[];
}

// Custom tooltip type definition
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<any>;
  label?: string;
}

// Conversation Modal Component
interface ConversationModalProps {
  isOpen: boolean;
  onClose: () => void;
  date: string;
  subreddit: string;
}

const ConversationModal: React.FC<ConversationModalProps> = ({ isOpen, onClose, date, subreddit }) => {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b">
          <h3 className="text-lg font-medium">
            Conversations from r/{subreddit} on {date}
          </h3>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
            aria-label="Close modal"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
            </svg>
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-9rem)]">
          <div className="bg-gray-50 p-4 rounded mb-4">
            <p className="text-sm text-gray-600">
              Showing conversations from {date} in r/{subreddit}.
            </p>
          </div>
          {/* This would be replaced with actual conversation data */}
          <div className="space-y-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <p className="text-gray-700">
                Loading conversations...
              </p>
            </div>
          </div>
        </div>
        <div className="border-t p-4 flex justify-end">
          <Button 
            onClick={onClose}
            variant="secondary"
            size="sm"
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

// SentimentTable component
const SentimentTable: React.FC<{ 
  data: TimeseriesData[];
  title?: string;
}> = ({ data, title }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;
  const totalPages = Math.ceil(data.length / rowsPerPage);
  
  const paginatedData = data.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );
  
  return (
    <div>
      {title && (
        <h4 className="text-base font-medium mb-3">{title}</h4>
      )}
      
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          <thead>
            <tr>
              <th className="py-2 px-4 border-b text-left text-sm font-medium text-gray-700">Date</th>
              <th className="py-2 px-4 border-b text-left text-sm font-medium text-gray-700">Sentiment</th>
              <th className="py-2 px-4 border-b text-left text-sm font-medium text-gray-700">Post Count</th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((item, idx) => (
              <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="py-2 px-4 border-b text-sm">{item.date}</td>
                <td className="py-2 px-4 border-b text-sm">{item.sentiment.toFixed(3)}</td>
                <td className="py-2 px-4 border-b text-sm">{item.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {totalPages > 1 && (
        <div className="mt-3 flex justify-between items-center">
          <div className="text-sm text-gray-500">
            Showing {(currentPage - 1) * rowsPerPage + 1} to {Math.min(currentPage * rowsPerPage, data.length)} of {data.length} entries
          </div>
          <div className="flex space-x-2">
            <Button
              onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
              disabled={currentPage === 1}
              variant="outline"
              size="sm"
            >
              Previous
            </Button>
            <Button
              onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
              disabled={currentPage === totalPages}
              variant="outline"
              size="sm"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

// Main component
const SentimentTimeseries: React.FC<SentimentTimeseriesProps> = ({
  subreddit,
  startDate,
  endDate,
  contentType = 'submissions',
  onEventSelect,
  initialViewMode = 'chart',
  showVisualization = true,
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [timeseriesData, setTimeseriesData] = useState<TimeseriesData[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [topWords, setTopWords] = useState<TopWordData>({ positive: [], negative: [] });
  const [showTable, setShowTable] = useState<boolean>(initialViewMode === 'table');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);

  // Force re-render function to help with chart issues
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const getTimeseriesData = async () => {
      if (!subreddit) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // First try the timeseries endpoint
        let data;
        try {
          data = await fetchSentimentTimeseries(subreddit, startDate, endDate, contentType);
        } catch (e) {
          console.warn('Error fetching from timeseries endpoint, falling back to sentiment endpoint', e);
          data = await fetchSentiment(subreddit, startDate, endDate, contentType);
        }
        
        // Fetch events for the timeline
        const eventsData = await fetchEvents(startDate, endDate);
        setEvents(eventsData);
        
        // Fetch trending words
        const sentimentKeywords = await fetchSentimentKeywords(subreddit);
        setTopWords({
          positive: sentimentKeywords.positive.slice(0, 5),
          negative: sentimentKeywords.negative.slice(0, 5)
        });
        
        if (!data || !Array.isArray(data)) {
          setError('Invalid data format received from API');
          setLoading(false);
          return;
        }
        
        // Format data for the chart
        const formattedData = data.map(item => {
          return {
            date: item.date,
            sentiment: item.avg_sentiment,
            count: item.post_count,
            isEvent: eventsData.some(event => event.date === item.date)
          };
        });
        
        if (formattedData.length === 0) {
          console.warn('No data points in formatted data');
        }
        
        setTimeseriesData(formattedData);
      } catch (err) {
        console.error('Error fetching sentiment timeseries:', err);
        setError('Failed to load sentiment timeseries data');
      } finally {
        setLoading(false);
      }
    };

    getTimeseriesData();
  }, [subreddit, startDate, endDate, contentType, refreshKey]);

  // Handler for clicking on chart points
  const handlePointClick = (data: any) => {
    if (!data) return;
    
    // Extract date from data, ensuring it's available
    const pointDate = data.date || (data.payload && data.payload.date);
    if (!pointDate) return;
    
    setSelectedDate(pointDate);
    setShowModal(true);
    
    // Check if there's an event on this date
    const eventOnDate = events.find(event => event.date === pointDate);
    
    if (eventOnDate && onEventSelect) {
      onEventSelect(pointDate);
    }
  };

  // Custom tooltip component
  const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      // Find events on this date
      const eventsOnDate = events.filter(event => event.date === label);
      
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow-md">
          <p className="font-medium mb-1">{label}</p>
          <p className="text-sm">Sentiment: <span className="font-medium">{payload[0].value.toFixed(3)}</span></p>
          <p className="text-sm">Posts: <span className="font-medium">{payload[1]?.payload?.count || 'N/A'}</span></p>
          
          {eventsOnDate.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-200">
              <p className="font-medium text-xs mb-1">Events:</p>
              <ul className="text-xs">
                {eventsOnDate.map((event, i) => (
                  <li key={i} className="mt-1">
                    <span className="inline-block px-1.5 py-0.5 rounded-full text-xs mr-1"
                          style={{
                            backgroundColor: getCategoryColor(event.category),
                            color: '#fff'
                          }}>
                      {event.category}
                    </span>
                    {event.event}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="mt-2 text-xs text-gray-500 italic">
            Click for conversations
          </div>
        </div>
      );
    }
    
    return null;
  };

  // Get color for event categories
  const getCategoryColor = (category: string): string => {
    const colorMap: Record<string, string> = {
      'politics': '#3b82f6',
      'economic': '#10b981',
      'pandemic': '#f59e0b',
      'technology': '#8b5cf6',
      'platform': '#ec4899',
      'gaming': '#f97316',
      'entertainment': '#06b6d4',
      'sports': '#14b8a6',
      'news': '#6366f1',
      'community': '#8b5cf6',
    };
    
    return colorMap[category?.toLowerCase()] || '#6b7280';
  };

  // Create an array of event markers for the chart
  const eventMarkers = timeseriesData
    .filter(point => events.some(event => event.date === point.date))
    .map(point => {
      const event = events.find(evt => evt.date === point.date);
      return {
        ...point,
        fillColor: "#f97316" // Use orange for all event points
      };
    });

  if (loading) {
    return <div className="text-center py-6">Loading sentiment data...</div>;
  }

  if (error) {
    return <div className="text-center py-6 text-red-500">{error}</div>;
  }

  // Use available timeseries data or empty array if none
  const displayData = timeseriesData.length > 0 ? timeseriesData : [];
  
  // Calculate statistics
  const avgSentiment = displayData.length > 0 
    ? (displayData.reduce((sum, item) => sum + item.sentiment, 0) / displayData.length).toFixed(3)
    : 'N/A';
  
  const totalPosts = displayData.reduce((sum, item) => sum + item.count, 0);
  
  const sentimentTrend = displayData.length > 1
    ? (displayData[displayData.length - 1].sentiment > displayData[0].sentiment
        ? 'Improving'
        : displayData[displayData.length - 1].sentiment < displayData[0].sentiment
        ? 'Declining'
        : 'Stable')
    : 'N/A';

  return (
    <div>
      <h3 className="text-lg font-medium mb-4">
        Sentiment Analysis for r/{subreddit} - {contentType === 'submissions' ? 'Posts' : 'Comments'}
      </h3>

      {/* Stats Cards for Quick Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
          <div className="text-sm text-gray-500">Average Sentiment</div>
          <div className="text-lg font-bold mt-1">{avgSentiment}</div>
        </div>
        
        <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
          <div className="text-sm text-gray-500">Data Points</div>
          <div className="text-lg font-bold mt-1">{displayData.length}</div>
        </div>
        
        <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
          <div className="text-sm text-gray-500">Total Posts Analyzed</div>
          <div className="text-lg font-bold mt-1">{totalPosts}</div>
        </div>
        
        <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200">
          <div className="text-sm text-gray-500">Sentiment Trend</div>
          <div className="text-lg font-bold mt-1 flex items-center">
            {sentimentTrend === 'Improving' ? (
              <>
                <span className="text-green-500">↗</span>
                <span className="ml-1">Improving</span>
              </>
            ) : sentimentTrend === 'Declining' ? (
              <>
                <span className="text-red-500">↘</span>
                <span className="ml-1">Declining</span>
              </>
            ) : (
              <>
                <span className="text-gray-500">→</span>
                <span className="ml-1">Stable</span>
              </>
            )}
          </div>
        </div>
      </div>

      {showVisualization && (
        <>
          {/* View Toggle Controls */}
          <div className="flex justify-end mb-4">
            <Button 
              onClick={() => setShowTable(!showTable)}
              variant="outline"
              size="sm"
            >
              {showTable ? 'Show Chart' : 'Show Table'}
            </Button>
          </div>

          {showTable ? (
            <SentimentTable 
              data={displayData} 
              title={`Sentiment Data for r/${subreddit}`} 
            />
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
              <div style={{ width: '100%', height: 400 }}>
                <ResponsiveContainer>
                  <LineChart
                    data={displayData}
                    margin={{ top: 10, right: 30, left: 10, bottom: 30 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
                    <XAxis 
                      dataKey="date" 
                      angle={-45} 
                      textAnchor="end" 
                      height={60}
                      tick={{ fontSize: 12 }}
                      tickMargin={10}
                    />
                    <YAxis 
                      domain={['auto', 'auto']} 
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => value.toFixed(2)}
                    />
                    <YAxis 
                      yAxisId="right" 
                      orientation="right" 
                      domain={['auto', 'auto']} 
                      hide={true} 
                    />
                    <Tooltip content={<CustomTooltip />} />
                    
                    {/* Main sentiment line */}
                    <Line 
                      type="monotone" 
                      dataKey="sentiment" 
                      stroke="#4f46e5" 
                      strokeWidth={2}
                      dot={{ 
                        r: 3, 
                        fill: "#4f46e5",
                        stroke: "white",
                        strokeWidth: 1,
                        cursor: 'pointer',
                      }}
                      activeDot={{ 
                        r: 5, 
                        fill: "#4f46e5",
                        stroke: "white",
                        strokeWidth: 1,
                        onClick: (_, payload) => handlePointClick(payload),
                      }}
                      isAnimationActive={false}
                    />
                    
                    {/* Hidden line for post count for tooltip */}
                    <Line 
                      type="monotone" 
                      dataKey="count" 
                      yAxisId="right"
                      hide={true}
                    />
                    
                    {/* Event markers as scatter points */}
                    <Scatter
                      data={eventMarkers}
                      fill="#f97316"
                      shape={(props) => {
                        const { cx, cy, payload } = props;
                        return (
                          <circle 
                            cx={cx} 
                            cy={cy} 
                            r={8} 
                            fill="#f97316" 
                            stroke="#ffffff"
                            strokeWidth={2}
                            onClick={() => handlePointClick(payload)}
                            style={{ cursor: 'pointer' }}
                          />
                        );
                      }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}

      {/* Trending Words Section */}
      {showVisualization && (
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
            <h4 className="font-medium text-green-700 border-b border-green-100 pb-2 mb-3">
              Top Positive Words
            </h4>
            <div className="flex flex-wrap gap-2">
              {topWords.positive.length > 0 ? (
                topWords.positive.map((word, index) => (
                  <div 
                    key={index}
                    className="px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm"
                  >
                    {word.keyword}
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm">No positive keywords found</p>
              )}
            </div>
          </div>
          
          <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
            <h4 className="font-medium text-red-700 border-b border-red-100 pb-2 mb-3">
              Top Negative Words
            </h4>
            <div className="flex flex-wrap gap-2">
              {topWords.negative.length > 0 ? (
                topWords.negative.map((word, index) => (
                  <div 
                    key={index}
                    className="px-3 py-1 bg-red-50 text-red-700 rounded-full text-sm"
                  >
                    {word.keyword}
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm">No negative keywords found</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="font-medium mb-2">About Sentiment Analysis</h3>
        <p className="text-gray-600 text-sm">
          {showVisualization ? 
            `This ${showTable ? 'table' : 'chart'} displays the average sentiment value for r/${subreddit} over time.
            The colored dots represent significant events that may have influenced sentiment.` :
            `This analysis displays the average sentiment value for r/${subreddit} over time.
            The summary includes average sentiment and key statistics for the selected period.`
          }
        </p>
        {showVisualization && (
          <p className="text-gray-600 text-sm font-medium mt-2">
            Click on a data point to view conversations from that date and related events.
          </p>
        )}
      </div>

      {/* Conversation Modal */}
      <ConversationModal 
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        date={selectedDate || ''}
        subreddit={subreddit}
      />
    </div>
  );
};

export default SentimentTimeseries; 