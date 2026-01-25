import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line, PieChart, Pie, Cell,
  ResponsiveContainer
} from 'recharts';
import { TrendingUp, Users, Award, Target, BarChart3, RadarIcon } from 'lucide-react';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

export function StatsVisualization({ data }) {
  const [activeView, setActiveView] = useState('radar');
  
  // Check if data exists and has visualization_data
  if (!data || !data.visualization_data || !data.visualization_data.candidates) {
    return (
      <div className="no-data-message">
        <p>No visualization data available. Try asking for statistics again.</p>
      </div>
    );
  }
  
  const { candidates, summary } = data.visualization_data;
  
  // Check if we have valid data
  if (!candidates || candidates.length === 0) {
    return (
      <div className="no-data-message">
        <p>No candidate data available for visualization.</p>
      </div>
    );
  }
  
  // Prepare data for radar chart
  const radarData = candidates.map(candidate => {
    const dataPoint = { subject: candidate.name };
    if (candidate.scores) {
      Object.entries(candidate.scores).forEach(([key, value]) => {
        dataPoint[key] = typeof value === 'number' ? value : 0;
      });
    }
    dataPoint.fullMark = 100;
    return dataPoint;
  });
  
  // Prepare data for bar chart comparison
  const barData = candidates.flatMap(candidate => {
    if (!candidate.scores) return [];
    return Object.entries(candidate.scores).map(([category, score]) => ({
      candidate: candidate.name,
      category,
      score: typeof score === 'number' ? score : 0
    }));
  });
  
  // Prepare data for category averages
  const categoryAverages = summary && summary.average_scores ? 
    Object.entries(summary.average_scores).map(([category, score]) => ({
      category,
      score: typeof score === 'number' ? Number(score.toFixed(1)) : 0
    })) : [];
  
  // Prepare data for overall scores pie
  const overallScores = candidates.map(candidate => ({
    name: candidate.name,
    value: candidate.overall_score || 0
  }));
  
  return (
    <div className="stats-visualization">
      <div className="view-toggle">
        <button 
          className={activeView === 'radar' ? 'active' : ''}
          onClick={() => setActiveView('radar')}
        >
          <RadarIcon size={16} /> Radar View
        </button>
        <button 
          className={activeView === 'bar' ? 'active' : ''}
          onClick={() => setActiveView('bar')}
        >
          <BarChart3 size={16} /> Bar Chart
        </button>
        <button 
          className={activeView === 'overall' ? 'active' : ''}
          onClick={() => setActiveView('overall')}
        >
          <Award size={16} /> Overall Scores
        </button>
      </div>
      
      {activeView === 'radar' && (
        <div className="chart-container">
          <h3>Candidate Skills Radar Chart</h3>
          <ResponsiveContainer width="100%" height={400}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="subject" />
              <PolarRadiusAxis angle={30} domain={[0, 100]} />
              {radarData.length > 0 && Object.keys(radarData[0])
                .filter(key => key !== 'subject' && key !== 'fullMark')
                .map((category, idx) => (
                  <Radar
                    key={category}
                    name={category}
                    dataKey={category}
                    stroke={COLORS[idx % COLORS.length]}
                    fill={COLORS[idx % COLORS.length]}
                    fillOpacity={0.3}
                  />
                ))}
              <Legend />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
      
      {activeView === 'bar' && (
        <div className="chart-container">
          <h3>Detailed Comparison</h3>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="candidate" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              {barData.length > 0 && Array.from(new Set(barData.map(d => d.category))).map((category, idx) => (
                <Bar
                  key={category}
                  dataKey="score"
                  name={category}
                  fill={COLORS[idx % COLORS.length]}
                  stackId="a"
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      
      {activeView === 'overall' && (
        <div className="overall-view">
          <div className="chart-container">
            <h3>Overall Performance Scores</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={overallScores}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {overallScores.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`${value.toFixed(1)}%`, 'Score']} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <div className="summary-cards">
            <div className="summary-card">
              <Award size={24} />
              <h4>Top Candidate</h4>
              <p className="highlight">
                {summary?.top_candidate?.name || "N/A"}
              </p>
              <p className="score">
                {summary?.top_candidate?.overall_score?.toFixed(1) || "0"}%
              </p>
            </div>
            
            <div className="summary-card">
              <TrendingUp size={24} />
              <h4>Strongest Area</h4>
              <p className="highlight">
                {categoryAverages.length > 0 ? 
                  categoryAverages.reduce((a, b) => a.score > b.score ? a : b).category : "N/A"
                }
              </p>
              <p className="score">
                {categoryAverages.length > 0 ? 
                  Math.max(...categoryAverages.map(c => c.score)).toFixed(1) : "0"}%
              </p>
            </div>
            
            <div className="summary-card">
              <Target size={24} />
              <h4>Needs Improvement</h4>
              <p className="highlight">
                {categoryAverages.length > 0 ? 
                  categoryAverages.reduce((a, b) => a.score < b.score ? a : b).category : "N/A"
                }
              </p>
              <p className="score">
                {categoryAverages.length > 0 ? 
                  Math.min(...categoryAverages.map(c => c.score)).toFixed(1) : "0"}%
              </p>
            </div>
          </div>
        </div>
      )}
      
      {categoryAverages.length > 0 && (
        <div className="category-averages">
          <h3>Category Averages</h3>
          <div className="averages-grid">
            {categoryAverages.map((item, index) => (
              <div key={item.category} className="category-item">
                <div className="category-header">
                  <span className="category-name">{item.category}</span>
                  <span className="category-score">{item.score}%</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ 
                      width: `${item.score}%`, 
                      backgroundColor: COLORS[index % COLORS.length] 
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {summary?.recommendations && summary.recommendations.length > 0 && (
        <div className="recommendations">
          <h3>Recommendations</h3>
          <ul>
            {summary.recommendations.map((rec, index) => (
              <li key={index}>💡 {rec}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}