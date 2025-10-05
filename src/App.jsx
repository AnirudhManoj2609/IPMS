import React, { useState, useCallback, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, PieChart, Pie, Cell } from 'recharts';

const API_BASE_URL = "http://localhost:8001";
const DEMO_PROJECT_ID = "PROD-EPIC-2025";
const DEMO_MODE = true; // Set to false to use real backend

// Mock data for demo
const MOCK_TEAMS = [
    { _id: '1', team_name: 'Director Team', department: 'Creative', lead_name: 'James Cameron' },
    { _id: '2', team_name: 'Production Team', department: 'Logistics', lead_name: 'Kathleen Kennedy' },
    { _id: '3', team_name: 'VFX Team', department: 'Post-Production', lead_name: 'Dennis Muren' },
    { _id: '4', team_name: 'Camera Team', department: 'Cinematography', lead_name: 'Roger Deakins' },
    { _id: '5', team_name: 'Art Department', department: 'Design', lead_name: 'Rick Carter' },
    { _id: '6', team_name: 'Sound Team', department: 'Audio', lead_name: 'Ben Burtt' }
];

const generateMockSchedule = (dayNumber, delayHours = 0) => {
    const scenes = [
        'Hospital corridor chase sequence',
        'Rooftop confrontation scene',
        'Underground lab discovery',
        'City street explosion setup',
        'Emotional dialogue in café',
        'Car chase through downtown',
        'Warehouse fight choreography',
        'Beach sunset final scene'
    ];
    
    const adjustmentTypes = [
        'Compressed non-critical prep time',
        'Merged similar setup activities',
        'Prioritized hero shots first',
        'Added parallel team workflows',
        'Eliminated redundant reviews',
        'Fast-tracked approval process'
    ];

    const sceneForDay = scenes[Math.min(dayNumber - 1, scenes.length - 1)];
    
    const originalSchedule = {
        scene_focus: sceneForDay,
        teams: {}
    };
    
    const dynamicSchedule = {
        teams: {},
        adjustments_made: delayHours > 0 ? adjustmentTypes.slice(0, Math.min(3 + Math.floor(delayHours / 2), 6)) : ['No adjustments needed - on schedule'],
        delay_impact: delayHours > 0 
            ? `Schedule compressed by ${delayHours * 5}% to recover ${delayHours} hour delay. Focus shifted to critical path activities.`
            : 'Production is on schedule. All teams proceeding as planned.'
    };

    MOCK_TEAMS.forEach(team => {
        const baseTime = 480; // 8 AM in minutes
        const taskCount = 6 + Math.floor(Math.random() * 4);
        
        const originalTasks = [];
        const dynamicTasks = [];
        
        let currentTime = baseTime;
        
        for (let i = 0; i < taskCount; i++) {
            const duration = 30 + Math.floor(Math.random() * 60);
            const hours = Math.floor(currentTime / 60);
            const mins = currentTime % 60;
            const timeStr = `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
            
            const tasks = {
                'Director Team': [
                    'Scene blocking and rehearsal',
                    'Actor performance review',
                    'Shot list finalization',
                    'Creative problem solving',
                    'Dailies review session',
                    'Next day prep meeting'
                ],
                'Production Team': [
                    'Call time and safety briefing',
                    'Location logistics coordination',
                    'Equipment inventory check',
                    'Schedule adherence monitoring',
                    'Meal break coordination',
                    'Wrap and transport planning'
                ],
                'VFX Team': [
                    'Green screen setup verification',
                    'Motion capture calibration',
                    'On-set VFX supervision',
                    'Plate photography',
                    'Reference material capture',
                    'Technical review and notes'
                ],
                'Camera Team': [
                    'Camera rig assembly',
                    'Lens selection and testing',
                    'Lighting setup collaboration',
                    'Master shot coverage',
                    'Close-up photography',
                    'Equipment maintenance'
                ],
                'Art Department': [
                    'Set dressing completion',
                    'Prop placement and continuity',
                    'Background detail enhancement',
                    'Set strike preparation',
                    'Next location prep',
                    'Design consultation'
                ],
                'Sound Team': [
                    'Boom mic positioning',
                    'Wireless mic setup',
                    'Ambient sound recording',
                    'Sound quality monitoring',
                    'ADR notes compilation',
                    'Equipment wrap and storage'
                ]
            };
            
            const teamTasks = tasks[team.team_name] || ['General production task'];
            const taskName = teamTasks[i % teamTasks.length];
            
            originalTasks.push({
                time: timeStr,
                task: taskName,
                estimated_duration_minutes: duration
            });
            
            // Dynamic tasks - potentially different based on delay
            let adjustedDuration = duration;
            let status = 'pending';
            
            if (delayHours > 0 && Math.random() > 0.6) {
                adjustedDuration = Math.max(15, duration - Math.floor(duration * 0.2));
                status = 'adjusted';
            } else if (delayHours > 2 && Math.random() > 0.8) {
                status = 'new';
                adjustedDuration = 20;
            }
            
            dynamicTasks.push({
                time: timeStr,
                task: status === 'new' ? `Catch-up: ${taskName}` : taskName,
                estimated_duration_minutes: adjustedDuration,
                status: status
            });
            
            currentTime += duration;
            if (currentTime >= 780 && currentTime < 840) { // Lunch break
                currentTime = 840;
            }
        }
        
        originalSchedule.teams[team.team_name] = originalTasks;
        dynamicSchedule.teams[team.team_name] = dynamicTasks;
    });
    
    return { originalSchedule, dynamicSchedule };
};

// Utility Components
const StatusMessage = ({ status, message }) => {
    if (!message) return null;
    let style = "bg-blue-100 text-blue-700 border-blue-300";
    let icon = "ℹ️";
    if (status === 'success') {
        style = "bg-green-100 text-green-700 border-green-300";
        icon = "✓";
    }
    if (status === 'error') {
        style = "bg-red-100 text-red-700 border-red-300";
        icon = "✕";
    }
    if (status === 'loading') {
        style = "bg-yellow-100 text-yellow-700 border-yellow-300";
        icon = "⏳";
    }

    return (
        <div className={`p-4 rounded-lg font-medium text-sm my-4 border-2 ${style} animate-fade-in`} role="alert">
            <span className="mr-2 text-lg">{icon}</span>
            {message}
        </div>
    );
};

const Card = ({ title, children, className = '', badge = null }) => (
    <div className={`bg-white p-6 rounded-xl shadow-xl border border-gray-200 hover:shadow-2xl transition-shadow duration-300 ${className}`}>
        <div className="flex justify-between items-center mb-4 border-b pb-3">
            <h2 className="text-xl font-bold text-gray-800">{title}</h2>
            {badge && <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-bold">{badge}</span>}
        </div>
        {children}
    </div>
);

const LoadingSpinner = () => (
    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
);

// Enhanced Schedule Viewer with Advanced Visualizations
const ScheduleViewer = ({ onLog }) => {
    const [dayNumber, setDayNumber] = useState(1);
    const [scheduleData, setScheduleData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedTeam, setSelectedTeam] = useState('all');
    const [availableTeams, setAvailableTeams] = useState(MOCK_TEAMS);
    const [viewMode, setViewMode] = useState('comparison');
    const [delayHours, setDelayHours] = useState(0);
    const [completionStats, setCompletionStats] = useState({});

    const generateDynamicSchedule = useCallback(async (e) => {
        if (e) e.preventDefault();
        setIsLoading(true);
        setScheduleData(null);
        onLog('loading', `Generating dynamic schedule for Day ${dayNumber}...`);

        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1500));

        const { originalSchedule, dynamicSchedule } = generateMockSchedule(dayNumber, delayHours);
        
        // Calculate completion stats
        const stats = {};
        Object.keys(dynamicSchedule.teams).forEach(teamName => {
            const tasks = dynamicSchedule.teams[teamName];
            stats[teamName] = {
                total: tasks.length,
                completed: Math.floor(tasks.length * (0.3 + Math.random() * 0.4)),
                efficiency: 75 + Math.floor(Math.random() * 20)
            };
        });
        setCompletionStats(stats);

        setScheduleData({
            day_number: dayNumber,
            delay_hours: delayHours,
            original_schedule: originalSchedule,
            dynamic_schedule: dynamicSchedule,
            teams: MOCK_TEAMS.map(t => t.team_name)
        });

        onLog('success', `Dynamic schedule generated for Day ${dayNumber}. Current delay: ${delayHours}h`);
        setIsLoading(false);
    }, [dayNumber, delayHours, onLog]);

    const getChartData = () => {
        if (!scheduleData) return [];
        
        const teams = selectedTeam === 'all' 
            ? Object.keys(scheduleData.dynamic_schedule.teams)
            : [selectedTeam];

        return teams.map(teamName => {
            const originalTasks = scheduleData.original_schedule?.teams?.[teamName] || [];
            const dynamicTasks = scheduleData.dynamic_schedule?.teams?.[teamName] || [];
            
            return {
                team: teamName.replace(' Team', ''),
                originalTaskCount: originalTasks.length,
                dynamicTaskCount: dynamicTasks.length,
                originalDuration: originalTasks.reduce((sum, t) => sum + (t.estimated_duration_minutes || 0), 0),
                dynamicDuration: dynamicTasks.reduce((sum, t) => sum + (t.estimated_duration_minutes || 0), 0),
                efficiency: completionStats[teamName]?.efficiency || 80,
                completed: completionStats[teamName]?.completed || 0,
                total: completionStats[teamName]?.total || dynamicTasks.length
            };
        });
    };

    const getRadarData = () => {
        if (!scheduleData) return [];
        
        return Object.keys(scheduleData.dynamic_schedule.teams).map(teamName => {
            const tasks = scheduleData.dynamic_schedule.teams[teamName];
            const avgDuration = tasks.reduce((sum, t) => sum + (t.estimated_duration_minutes || 0), 0) / tasks.length;
            
            return {
                team: teamName.replace(' Team', ''),
                tasks: tasks.length,
                duration: Math.round(avgDuration),
                efficiency: completionStats[teamName]?.efficiency || 80,
                workload: Math.min(100, (tasks.length * avgDuration) / 10)
            };
        });
    };

    const getPieData = () => {
        if (!scheduleData) return [];
        
        return Object.keys(scheduleData.dynamic_schedule.teams).map(teamName => {
            const tasks = scheduleData.dynamic_schedule.teams[teamName];
            const totalDuration = tasks.reduce((sum, t) => sum + (t.estimated_duration_minutes || 0), 0);
            
            return {
                name: teamName.replace(' Team', ''),
                value: totalDuration
            };
        });
    };

    const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

    const ComparisonView = () => {
        const filtered = {
            original: selectedTeam === 'all' 
                ? scheduleData.original_schedule?.teams || {}
                : { [selectedTeam]: scheduleData.original_schedule?.teams?.[selectedTeam] || [] },
            dynamic: selectedTeam === 'all'
                ? scheduleData.dynamic_schedule?.teams || {}
                : { [selectedTeam]: scheduleData.dynamic_schedule?.teams?.[selectedTeam] || [] }
        };
        
        const teams = Object.keys(filtered.dynamic);

        return (
            <div className="space-y-6">
                {teams.map(teamName => {
                    const originalTasks = filtered.original[teamName] || [];
                    const dynamicTasks = filtered.dynamic[teamName] || [];
                    const stats = completionStats[teamName] || {};

                    return (
                        <div key={teamName} className="border-2 border-gray-200 rounded-xl p-5 bg-gradient-to-br from-white to-gray-50 hover:shadow-lg transition-all">
                            <div className="flex justify-between items-center mb-4">
                                <h4 className="text-xl font-bold text-gray-800">{teamName}</h4>
                                <div className="flex gap-4 text-sm">
                                    <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-semibold">
                                        {stats.completed || 0}/{stats.total || dynamicTasks.length} Complete
                                    </span>
                                    <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full font-semibold">
                                        {stats.efficiency || 80}% Efficient
                                    </span>
                                </div>
                            </div>
                            
                            <div className="grid md:grid-cols-2 gap-4">
                                <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border-l-4 border-blue-500 shadow-md">
                                    <h5 className="font-bold text-blue-900 mb-3 flex items-center">
                                        <span className="mr-2">📋</span> Original Schedule
                                    </h5>
                                    <ul className="space-y-2">
                                        {originalTasks.map((task, idx) => (
                                            <li key={idx} className="text-sm flex space-x-2 bg-white bg-opacity-50 p-2 rounded">
                                                <span className="font-mono text-blue-700 font-bold w-16">{task.time}</span>
                                                <span className="flex-1 text-gray-700">{task.task}</span>
                                                <span className="text-xs text-gray-500">{task.estimated_duration_minutes}m</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>

                                <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border-l-4 border-green-500 shadow-md">
                                    <h5 className="font-bold text-green-900 mb-3 flex items-center">
                                        <span className="mr-2">⚡</span> Adjusted Schedule
                                    </h5>
                                    <ul className="space-y-2">
                                        {dynamicTasks.map((task, idx) => (
                                            <li key={idx} className="text-sm flex space-x-2 bg-white bg-opacity-50 p-2 rounded">
                                                <span className="font-mono text-green-700 font-bold w-16">{task.time}</span>
                                                <span className="flex-1 text-gray-700">
                                                    {task.task}
                                                    {task.status === 'new' && (
                                                        <span className="ml-2 text-xs bg-yellow-400 text-yellow-900 px-2 py-0.5 rounded-full font-bold">NEW</span>
                                                    )}
                                                    {task.status === 'adjusted' && (
                                                        <span className="ml-2 text-xs bg-orange-400 text-orange-900 px-2 py-0.5 rounded-full font-bold">MODIFIED</span>
                                                    )}
                                                </span>
                                                <span className="text-xs text-gray-500">{task.estimated_duration_minutes}m</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    };

    const ChartView = () => {
        const chartData = getChartData();
        const radarData = getRadarData();
        const pieData = getPieData();

        return (
            <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                    <div className="bg-white p-5 rounded-xl border-2 border-gray-200 shadow-lg">
                        <h4 className="font-bold mb-4 text-lg text-gray-800">Task Count Analysis</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                <XAxis dataKey="team" angle={-20} textAnchor="end" height={80} style={{ fontSize: '12px' }} />
                                <YAxis />
                                <Tooltip contentStyle={{ backgroundColor: '#f9fafb', border: '1px solid #e5e7eb' }} />
                                <Legend />
                                <Bar dataKey="originalTaskCount" fill="#3b82f6" name="Original" radius={[8, 8, 0, 0]} />
                                <Bar dataKey="dynamicTaskCount" fill="#10b981" name="Adjusted" radius={[8, 8, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="bg-white p-5 rounded-xl border-2 border-gray-200 shadow-lg">
                        <h4 className="font-bold mb-4 text-lg text-gray-800">Duration Comparison</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                <XAxis dataKey="team" angle={-20} textAnchor="end" height={80} style={{ fontSize: '12px' }} />
                                <YAxis />
                                <Tooltip contentStyle={{ backgroundColor: '#f9fafb', border: '1px solid #e5e7eb' }} />
                                <Legend />
                                <Line type="monotone" dataKey="originalDuration" stroke="#3b82f6" name="Original (min)" strokeWidth={3} dot={{ r: 5 }} />
                                <Line type="monotone" dataKey="dynamicDuration" stroke="#10b981" name="Adjusted (min)" strokeWidth={3} dot={{ r: 5 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                    <div className="bg-white p-5 rounded-xl border-2 border-gray-200 shadow-lg">
                        <h4 className="font-bold mb-4 text-lg text-gray-800">Team Performance Radar</h4>
                        <ResponsiveContainer width="100%" height={350}>
                            <RadarChart data={radarData}>
                                <PolarGrid stroke="#e5e7eb" />
                                <PolarAngleAxis dataKey="team" style={{ fontSize: '11px' }} />
                                <PolarRadiusAxis />
                                <Radar name="Efficiency" dataKey="efficiency" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} />
                                <Radar name="Workload" dataKey="workload" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.4} />
                                <Legend />
                                <Tooltip />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="bg-white p-5 rounded-xl border-2 border-gray-200 shadow-lg">
                        <h4 className="font-bold mb-4 text-lg text-gray-800">Time Distribution</h4>
                        <ResponsiveContainer width="100%" height={350}>
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {pieData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <Card title="Daily Schedule Generator & Comparison" badge={DEMO_MODE ? "DEMO MODE" : "LIVE"} className="lg:col-span-3">
            <form onSubmit={generateDynamicSchedule} className="space-y-4 mb-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-2">Shoot Day</label>
                        <input 
                            type="number" 
                            placeholder="Day Number"
                            value={dayNumber}
                            onChange={(e) => setDayNumber(Number(e.target.value))}
                            min="1"
                            max="30"
                            required
                            className="w-full p-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-2">Current Delay (hours)</label>
                        <input 
                            type="number" 
                            placeholder="Delay Hours"
                            value={delayHours}
                            onChange={(e) => setDelayHours(Number(e.target.value))}
                            min="0"
                            max="12"
                            className="w-full p-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        />
                    </div>
                    <div className="flex items-end">
                        <button 
                            type="submit" 
                            disabled={isLoading || dayNumber < 1}
                            className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-3 rounded-lg font-bold hover:from-blue-700 hover:to-blue-800 transition-all duration-200 disabled:opacity-50 flex items-center justify-center shadow-lg hover:shadow-xl"
                        >
                            {isLoading ? <LoadingSpinner /> : `Generate Schedule`}
                        </button>
                    </div>
                </div>
            </form>

            {scheduleData && (
                <>
                    <div className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 text-white p-6 rounded-xl mb-6 shadow-2xl">
                        <div className="grid md:grid-cols-4 gap-6">
                            <div className="text-center">
                                <p className="text-sm font-semibold opacity-90 mb-1">Shoot Day</p>
                                <p className="text-4xl font-extrabold">{scheduleData.day_number}</p>
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-semibold opacity-90 mb-1">Current Delay</p>
                                <p className="text-4xl font-extrabold">{scheduleData.delay_hours}h</p>
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-semibold opacity-90 mb-1">Teams Active</p>
                                <p className="text-4xl font-extrabold">{Object.keys(scheduleData.dynamic_schedule.teams).length}</p>
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-semibold opacity-90 mb-1">Total Tasks</p>
                                <p className="text-4xl font-extrabold">
                                    {Object.values(scheduleData.dynamic_schedule.teams).reduce((sum, tasks) => sum + tasks.length, 0)}
                                </p>
                            </div>
                        </div>
                        
                        <div className="mt-6 pt-6 border-t border-white border-opacity-30">
                            <p className="text-sm font-semibold mb-2">Scene Focus:</p>
                            <p className="text-lg font-bold">{scheduleData.original_schedule?.scene_focus}</p>
                        </div>

                        {scheduleData.dynamic_schedule?.adjustments_made && (
                            <div className="mt-4 bg-white bg-opacity-20 backdrop-blur-sm p-4 rounded-lg">
                                <p className="text-sm font-bold mb-2">Active Adjustments:</p>
                                <ul className="grid md:grid-cols-2 gap-2 text-sm">
                                    {scheduleData.dynamic_schedule.adjustments_made.map((adj, idx) => (
                                        <li key={idx} className="flex items-start">
                                            <span className="mr-2">✓</span>
                                            <span>{adj}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-3 md:space-y-0 mb-6 bg-gray-50 p-4 rounded-lg">
                        <div className="flex space-x-2">
                            <button
                                onClick={() => setViewMode('comparison')}
                                className={`px-6 py-2 rounded-lg font-bold transition-all ${
                                    viewMode === 'comparison' 
                                        ? 'bg-blue-600 text-white shadow-lg scale-105' 
                                        : 'bg-white text-gray-700 hover:bg-gray-100 border-2 border-gray-200'
                                }`}
                            >
                                📋 Comparison
                            </button>
                            <button
                                onClick={() => setViewMode('chart')}
                                className={`px-6 py-2 rounded-lg font-bold transition-all ${
                                    viewMode === 'chart' 
                                        ? 'bg-blue-600 text-white shadow-lg scale-105' 
                                        : 'bg-white text-gray-700 hover:bg-gray-100 border-2 border-gray-200'
                                }`}
                            >
                                📊 Analytics
                            </button>
                        </div>

                        <select
                            value={selectedTeam}
                            onChange={(e) => setSelectedTeam(e.target.value)}
                            className="p-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-semibold"
                        >
                            <option value="all">All Teams</option>
                            {availableTeams.map(team => (
                                <option key={team._id} value={team.team_name}>
                                    {team.team_name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="animate-fade-in">
                        {viewMode === 'comparison' ? <ComparisonView /> : <ChartView />}
                    </div>
                </>
            )}
        </Card>
    );
};

// Main App
const App = () => {
    const [status, setStatus] = useState({ 
        status: 'info', 
        message: DEMO_MODE 
            ? 'Demo Mode Active - Experience realistic production scheduling with simulated data'
            : `Project ID: ${DEMO_PROJECT_ID}. Backend: ${API_BASE_URL}` 
    });

    const handleLog = (type, message) => {
        setStatus({ status: type, message: message });
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-4 sm:p-8">
            <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDE0YzMuMzE0IDAgNiAyLjY4NiA2IDZzLTIuNjg2IDYtNiA2LTYtMi42ODYtNi02IDIuNjg2LTYgNi02ek0yNCAzOGMzLjMxNCAwIDYgMi42ODYgNiA2cy0yLjY4NiA2LTYgNi02LTIuNjg2LTYtNiAyLjY4Ni02IDYtNnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-40"></div>
            
            <header className="mb-8 max-w-7xl mx-auto relative z-10">
                <div className="text-center mb-6">
                    <div className="inline-block bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-2 rounded-full text-sm font-bold mb-4 shadow-lg">
                        AI-Powered Production Management
                    </div>
                    <h1 className="text-5xl sm:text-6xl font-extrabold text-white mb-3 drop-shadow-2xl">
                        Production Scheduler
                    </h1>
                    <p className="text-xl text-gray-300 font-medium">
                        Dynamic schedule generation with real-time delay adaptation
                    </p>
                </div>
                {DEMO_MODE && (
                    <div className="bg-yellow-400 bg-opacity-20 backdrop-blur-sm border-2 border-yellow-400 text-yellow-100 p-4 rounded-xl text-center font-semibold max-w-2xl mx-auto">
                        Demo Mode: All data is simulated for demonstration purposes
                    </div>
                )}
            </header>

            <main className="max-w-7xl mx-auto relative z-10">
                <StatusMessage status={status.status} message={status.message} />
                
                <div className="mb-8">
                    <ScheduleViewer onLog={handleLog} />
                </div>

                {DEMO_MODE && (
                    <Card title="How It Works" className="bg-gradient-to-br from-indigo-50 to-purple-50">
                        <div className="grid md:grid-cols-3 gap-6">
                            <div className="text-center p-4">
                                <div className="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-3 shadow-lg">
                                    1
                                </div>
                                <h3 className="font-bold text-lg mb-2">Select Day & Delay</h3>
                                <p className="text-gray-600 text-sm">
                                    Choose your shoot day and input any production delays
                                </p>
                            </div>
                            <div className="text-center p-4">
                                <div className="w-16 h-16 bg-purple-500 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-3 shadow-lg">
                                    2
                                </div>
                                <h3 className="font-bold text-lg mb-2">AI Generates Schedule</h3>
                                <p className="text-gray-600 text-sm">
                                    System analyzes and creates optimized team schedules
                                </p>
                            </div>
                            <div className="text-center p-4">
                                <div className="w-16 h-16 bg-pink-500 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-3 shadow-lg">
                                    3
                                </div>
                                <h3 className="font-bold text-lg mb-2">Compare & Adjust</h3>
                                <p className="text-gray-600 text-sm">
                                    View side-by-side comparisons with visual analytics
                                </p>
                            </div>
                        </div>
                        
                        <div className="mt-6 pt-6 border-t border-gray-300">
                            <h3 className="font-bold text-lg mb-3 text-center">Key Features</h3>
                            <div className="grid md:grid-cols-2 gap-3 text-sm">
                                <div className="flex items-center space-x-2 bg-white p-3 rounded-lg shadow">
                                    <span className="text-green-500 font-bold">✓</span>
                                    <span>Multi-team coordination and task scheduling</span>
                                </div>
                                <div className="flex items-center space-x-2 bg-white p-3 rounded-lg shadow">
                                    <span className="text-green-500 font-bold">✓</span>
                                    <span>Real-time delay impact analysis</span>
                                </div>
                                <div className="flex items-center space-x-2 bg-white p-3 rounded-lg shadow">
                                    <span className="text-green-500 font-bold">✓</span>
                                    <span>Visual analytics with multiple chart types</span>
                                </div>
                                <div className="flex items-center space-x-2 bg-white p-3 rounded-lg shadow">
                                    <span className="text-green-500 font-bold">✓</span>
                                    <span>Team performance and efficiency tracking</span>
                                </div>
                            </div>
                        </div>
                    </Card>
                )}
            </main>

            <style>{`
                @keyframes fade-in {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .animate-fade-in {
                    animation: fade-in 0.5s ease-out;
                }
            `}</style>
        </div>
    );
};

export default App;