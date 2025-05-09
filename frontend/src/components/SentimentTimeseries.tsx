import React, { useState, useEffect } from 'react';
import { fetchSentimentTimeseries } from '../api/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

interface SentimentTimeseriesProps {
  subreddit: string;
  startDate: string;
  endDate: string;
  contentType?: string;
  onEventSelect?: (eventDate: string) => void;
}

const SentimentTimeseries: React.FC<SentimentTimeseriesProps> = ({
  subreddit,
  startDate,
  endDate,
  contentType = 'submissions',
  onEventSelect,
}) => {
  const [timeseriesData, setTimeseriesData] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredEvent, setHoveredEvent] = useState<string | null>(null);

  useEffect(() => {
    const getTimeseriesData = async () => {
      if (!subreddit) {
        setLoading(false);
        return;
      }
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchSentimentTimeseries(subreddit, startDate, endDate, contentType);
        
        // Format the data for the chart
        const formattedData = data.map(item => ({
          date: item.date,
          sentiment: item.avg_sentiment,
          postCount: item.post_count,
          events: item.events,
          // Generate a tooltip with all events on this date
          eventText: item.events && item.events.length > 0
            ? item.events.map((e: any) => e.event).join(', ')
            : null,
        }));
        
        setTimeseriesData(formattedData);
      } catch (err) {
        console.error('Error fetching sentiment timeseries:', err);
        setError('Failed to load timeseries data');
      } finally {
        setLoading(false);
      }
    };

    getTimeseriesData();
  }, [subreddit, startDate, endDate, contentType]);

  const handleEventClick = (date: string) => {
    if (onEventSelect) {
      onEventSelect(date);
    }
  };

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

  if (timeseriesData.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="bg-[var(--scale-bg-light)] p-8 rounded-lg">
          <h3 className="text-lg font-medium mb-2">No Data Available</h3>
          <p className="text-[var(--scale-text-secondary)]">
            No timeseries data is available for r/{subreddit} during this period ({startDate} to {endDate}).
          </p>
        </div>
      </div>
    );
  }

  // Find dates with events to mark on the chart
  const eventDates = timeseriesData.filter(item => item.events && item.events.length > 0)
    .map(item => item.date);

  // Custom tooltip to show event information
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const dataPoint = timeseriesData.find(item => item.date === label);
      
      return (
        <div className="bg-white p-4 shadow-xl rounded-lg border border-[var(--scale-border)]">
          <p className="font-medium mb-1">{label}</p>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-[var(--scale-accent)]"></div>
            <p className="text-sm">
              Sentiment: <span className="font-semibold">{payload[0].value.toFixed(3)}</span>
            </p>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 rounded-full bg-[#8884d8] opacity-60"></div>
            <p className="text-sm">
              Posts: <span className="font-semibold">{dataPoint?.postCount || 0}</span>
            </p>
          </div>
          
          {dataPoint?.events && dataPoint.events.length > 0 && (
            <div className="mt-3 pt-2 border-t border-[var(--scale-border)]">
              <p className="font-medium text-sm mb-1">Events:</p>
              <ul className="text-xs">
                {dataPoint.events.map((event: any, idx: number) => (
                  <li key={idx} className="mt-1 flex items-center gap-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${getCategoryColor(event.category)}`}></span>
                    {event.event} <span className="text-[var(--scale-text-light)]">({event.category})</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleEventClick(label)}
                className="mt-2 px-3 py-1 text-xs bg-[var(--scale-accent)] hover:bg-[var(--scale-accent-light)] text-white rounded-full transition-colors"
              >
                View conversations
              </button>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  // Find min and max sentiment values for y-axis configuration
  const sentiments = timeseriesData.map(item => item.sentiment);
  const minSentiment = Math.min(...sentiments) - 0.1;
  const maxSentiment = Math.max(...sentiments) + 0.1;

  // Custom tick formatter for X axis to prevent overcrowding
  const formatXAxis = (value: string) => {
    // Show only some of the dates to avoid overcrowding
    const idx = timeseriesData.findIndex(item => item.date === value);
    if (timeseriesData.length <= 10 || idx % Math.ceil(timeseriesData.length / 10) === 0) {
      return value;
    }
    return '';
  };

  // Create a custom dot component for better click handling
  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    const isEvent = payload && payload.date && eventDates.includes(payload.date);
    
    if (!isEvent) {
      return (
        <circle 
          cx={cx} 
          cy={cy} 
          r={5}
          fill="var(--scale-accent)"
        />
      );
    }
    
    return (
      <g 
        transform={`translate(${cx},${cy})`}
        onClick={() => {
          console.log("Group clicked for date:", payload.date);
          handleEventClick(payload.date);
        }}
        style={{ cursor: 'pointer' }}
      >
        {/* Larger invisible hit area */}
        <circle r={20} fill="transparent" />
        
        {/* Visible dot */}
        <circle
          r={8}
          fill="#FF5722"
          stroke="#fff"
          strokeWidth={2}
        />
      </g>
    );
  };

  return (
    <div className="pb-4">
      <div style={{ width: '100%', height: 400 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={timeseriesData}
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
            <Legend />
            
            {/* Event reference lines */}
            {eventDates.map(date => (
              <ReferenceLine
                key={date}
                x={date}
                stroke={hoveredEvent === date ? "#FF5722" : "var(--scale-accent)"}
                strokeWidth={hoveredEvent === date ? 2 : 1}
                strokeDasharray={hoveredEvent === date ? "4 4" : "3 3"}
                label={false}
                isFront={true}
                onClick={() => handleEventClick(date)}
                onMouseOver={() => setHoveredEvent(date)}
                onMouseOut={() => setHoveredEvent(null)}
                style={{ 
                  cursor: 'pointer',
                  transition: 'stroke 0.2s ease-in-out, stroke-width 0.2s ease-in-out, stroke-dasharray 0.2s ease-in-out'
                }}
              />
            ))}
            
            <Line
              type="monotone"
              dataKey="sentiment"
              name="Sentiment"
              stroke="var(--scale-accent)"
              dot={<CustomDot />}
              activeDot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {/* Event legend */}
      <div className="flex items-center justify-center mt-4">
        <div className="flex items-center mr-4">
          <div className="w-3 h-3 rounded-full bg-[#FF5722] mr-1"></div>
          <span className="text-xs text-[var(--scale-text-light)]">Event</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 rounded-full bg-[var(--scale-accent)] mr-1"></div>
          <span className="text-xs text-[var(--scale-text-light)]">Regular data point</span>
        </div>
      </div>
      
      {/* Hint text */}
      <div className="text-center mt-2">
        <span className="text-xs text-[var(--scale-text-light)] bg-[var(--scale-bg-light)] py-2 px-4 rounded-full inline-block">
          Click on orange points (events) to view related conversations
        </span>
      </div>
    </div>
  );
};

// Helper function for event category colors
const getCategoryColor = (category: string) => {
  switch (category?.toLowerCase()) {
    case 'politics':
      return 'bg-blue-500';
    case 'economic':
      return 'bg-green-500';
    case 'pandemic':
      return 'bg-red-500';
    case 'technology':
      return 'bg-purple-500';
    case 'platform':
      return 'bg-yellow-500';
    default:
      return 'bg-gray-500';
  }
};

export default SentimentTimeseries; 