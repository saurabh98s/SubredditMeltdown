import React from 'react';

interface SentimentData {
  date: string;
  sentiment: number;
  count: number;
}

interface SimpleSentimentVisualizationProps {
  data: SentimentData[];
  title: string;
}

const SimpleSentimentVisualization: React.FC<SimpleSentimentVisualizationProps> = ({ data, title }) => {
  // Find the min and max sentiment values to scale the visualization
  let minSentiment = 0;
  let maxSentiment = 0;
  
  if (data.length > 0) {
    minSentiment = Math.min(...data.map(item => item.sentiment));
    maxSentiment = Math.max(...data.map(item => item.sentiment));
    
    // Ensure the range is not zero (for scaling)
    if (minSentiment === maxSentiment) {
      minSentiment -= 0.1;
      maxSentiment += 0.1;
    }
  }
  
  // Scale sentiment values to 0-100 for display
  const getScaledValue = (sentiment: number): number => {
    const range = maxSentiment - minSentiment;
    return Math.round(((sentiment - minSentiment) / range) * 100);
  };
  
  // Get color based on sentiment value
  const getSentimentColor = (sentiment: number): string => {
    if (sentiment > 0.05) return '#4ade80'; // green for positive
    if (sentiment < -0.05) return '#f87171'; // red for negative
    return '#a3a3a3'; // gray for neutral
  };

  // Generate CSV string from data
  const generateCsv = (): string => {
    // Create CSV header
    let csv = 'Date,Sentiment,Count\n';
    
    // Add data rows
    data.forEach(item => {
      csv += `${item.date},${item.sentiment},${item.count}\n`;
    });
    
    return csv;
  };
  
  // Handle download CSV button click
  const handleDownloadCsv = () => {
    // Generate CSV content
    const csvContent = generateCsv();
    
    // Create a Blob with the CSV content
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // Create a link element and trigger download
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `sentiment-data-${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">{title}</h3>
        
        {data.length > 0 && (
          <button
            onClick={handleDownloadCsv}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm flex items-center"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download CSV
          </button>
        )}
      </div>
      
      {data.length === 0 ? (
        <div className="text-center py-4 bg-gray-100 rounded">
          No data available
        </div>
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div className="bg-white p-3 rounded shadow">
              <div className="text-sm text-gray-500">Min Sentiment</div>
              <div className="font-medium">{minSentiment.toFixed(3)}</div>
            </div>
            <div className="bg-white p-3 rounded shadow">
              <div className="text-sm text-gray-500">Max Sentiment</div>
              <div className="font-medium">{maxSentiment.toFixed(3)}</div>
            </div>
          </div>
          
          <div className="border rounded overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sentiment
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Count
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Visualization
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.map((item, index) => (
                  <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {item.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span 
                        className="px-2 py-1 rounded text-white"
                        style={{ backgroundColor: getSentimentColor(item.sentiment) }}
                      >
                        {item.sentiment.toFixed(3)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {item.count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="w-full bg-gray-200 h-4 rounded-full overflow-hidden">
                        <div 
                          className="h-full" 
                          style={{ 
                            width: `${getScaledValue(item.sentiment)}%`,
                            backgroundColor: getSentimentColor(item.sentiment),
                            minWidth: '2px'
                          }}
                        ></div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="mt-4 p-4 bg-gray-100 rounded text-sm text-gray-600">
            <p>This is a simple table visualization of sentiment data. The visualization column shows the relative sentiment scale from lowest to highest value in the dataset.</p>
          </div>
        </>
      )}
    </div>
  );
};

export default SimpleSentimentVisualization; 