import { useState, useEffect } from 'react';
import { fetchEvents, EventData } from '../api/api';
import { format, parseISO } from 'date-fns';

interface EventOverlayProps {
  startDate: string;
  endDate: string;
  selectedCategories: string[];
  onCategoryChange: (categories: string[]) => void;
}

const EventOverlay: React.FC<EventOverlayProps> = ({
  startDate,
  endDate,
  selectedCategories,
  onCategoryChange,
}) => {
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);

  useEffect(() => {
    const fetchEventData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchEvents(startDate, endDate);
        setEvents(data);
        
        // Extract unique categories
        const categories = Array.from(new Set(data.map(event => event.category)));
        setAvailableCategories(categories);
      } catch (err) {
        setError('Failed to load event data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchEventData();
  }, [startDate, endDate]);

  const toggleCategory = (category: string) => {
    if (selectedCategories.includes(category)) {
      onCategoryChange(selectedCategories.filter(c => c !== category));
    } else {
      onCategoryChange([...selectedCategories, category]);
    }
  };

  // Filter events by selected categories
  const filteredEvents = events.filter(event => 
    selectedCategories.includes(event.category)
  );

  const formatDate = (dateStr: string) => {
    try {
      return format(parseISO(dateStr), 'MMM d, yyyy');
    } catch (e) {
      return dateStr;
    }
  };

  if (loading) {
    return <div className="mt-4 text-center">Loading events...</div>;
  }

  if (error) {
    return <div className="mt-4 text-red-500">{error}</div>;
  }

  return (
    <div className="mt-6">
      <div className="mb-4">
        <h3 className="text-md font-medium text-gray-700 mb-2">Event Categories</h3>
        <div className="flex flex-wrap gap-2">
          {availableCategories.map(category => (
            <button
              key={category}
              className={`px-3 py-1 rounded-full text-sm ${
                selectedCategories.includes(category)
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 text-gray-700'
              }`}
              onClick={() => toggleCategory(category)}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-gray-200 pt-4">
        <h3 className="text-md font-medium text-gray-700 mb-2">Major Events</h3>
        {filteredEvents.length === 0 ? (
          <p className="text-gray-500">No events found for the selected categories and date range.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredEvents.map(event => (
              <div key={`${event.date}-${event.event}`} className="bg-gray-50 p-3 rounded-md">
                <div className="flex items-center">
                  <div
                    className="w-3 h-3 rounded-full mr-2"
                    style={{
                      backgroundColor: getCategoryColor(event.category),
                    }}
                  />
                  <span className="text-sm text-gray-500">{formatDate(event.date)}</span>
                </div>
                <p className="mt-1 text-sm">{event.event}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Helper function to get color based on category
function getCategoryColor(category: string): string {
  const colorMap: { [key: string]: string } = {
    politics: '#4C51BF', // indigo
    pandemic: '#E53E3E', // red
    economic: '#38A169', // green
    technology: '#D69E2E', // yellow
    social: '#ED8936', // orange
    environment: '#48BB78', // green
    sports: '#9F7AEA', // purple
  };

  return colorMap[category.toLowerCase()] || '#718096'; // default gray
}

export default EventOverlay; 