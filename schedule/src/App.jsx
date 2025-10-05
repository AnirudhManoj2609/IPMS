import React, { useState, useCallback } from 'react';

// Base URL for the new scheduling FastAPI server
const API_BASE_URL = "http://localhost:8001"; // Assuming the scheduler runs on port 8001
const DEMO_PROJECT_ID = "PROD-EPIC-2025";

// --- Utility Components ---

const StatusMessage = ({ status, message }) => {
    if (!message) return null;
    let style = "bg-blue-100 text-blue-700";
    if (status === 'success') style = "bg-green-100 text-green-700";
    if (status === 'error') style = "bg-red-100 text-red-700";
    if (status === 'loading') style = "bg-yellow-100 text-yellow-700";

    return (
        <div className={`p-3 rounded-lg font-medium text-sm my-4 ${style}`} role="alert">
            {message}
        </div>
    );
};

const Card = ({ title, children, className = '' }) => (
    <div className={`bg-white p-6 rounded-xl shadow-lg border border-gray-100 ${className}`}>
        <h2 className="text-xl font-bold text-gray-800 mb-4 border-b pb-2">{title}</h2>
        {children}
    </div>
);

const LoadingSpinner = () => (
    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
);

// --- Component 1: Team Input ---

const TeamInputForm = ({ onLog }) => {
    const [teamName, setTeamName] = useState('');
    const [department, setDepartment] = useState('');
    const [leadName, setLeadName] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Adding production team...');

        const payload = {
            project_id: DEMO_PROJECT_ID,
            team_name: teamName,
            department: department,
            lead_name: leadName
        };

        try {
            const response = await fetch(`${API_BASE_URL}/teams/add/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to add team.');
            }

            onLog('success', result.message);
            setTeamName('');
            setDepartment('');
            setLeadName('');
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="1. Add Production Team">
            <form onSubmit={handleSubmit} className="space-y-3">
                <input 
                    type="text" 
                    placeholder="Team Name (e.g., VFX Team)"
                    value={teamName}
                    onChange={(e) => setTeamName(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded focus:ring-indigo-500 focus:border-indigo-500"
                />
                <input 
                    type="text" 
                    placeholder="Department (e.g., Post-Production)"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded focus:ring-indigo-500 focus:border-indigo-500"
                />
                 <input 
                    type="text" 
                    placeholder="Team Lead Name"
                    value={leadName}
                    onChange={(e) => setLeadName(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="w-full bg-indigo-600 text-white p-2 rounded font-semibold hover:bg-indigo-700 transition duration-150 disabled:opacity-50 flex items-center justify-center"
                >
                    {isLoading ? <LoadingSpinner /> : 'Add Team'}
                </button>
            </form>
            <p className="text-sm text-gray-500 mt-3">Add all teams (e.g., Production, Director, Media, VFX, Art, etc.) before generating a schedule.</p>
        </Card>
    );
};

// --- Component 2: Script and Plan Input ---

const ScriptInputForm = ({ onLog }) => {
    const [scriptText, setScriptText] = useState('');
    const [plannedSchedule, setPlannedSchedule] = useState('{"day_1": "Shoot Scenes 1-5 (Park)"}');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Uploading script and initial plan...');

        let parsedPlan;
        try {
            parsedPlan = JSON.parse(plannedSchedule);
        } catch (error) {
            onLog('error', 'Initial Planned Schedule must be valid JSON format.');
            setIsLoading(false);
            return;
        }

        const payload = {
            project_id: DEMO_PROJECT_ID,
            script_text: scriptText,
            initial_planned_schedule: parsedPlan
        };

        try {
            const response = await fetch(`${API_BASE_URL}/script/upload/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to upload script.');
            }

            onLog('success', result.message);
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="2. Upload Script & Initial Plan" className="lg:col-span-2">
            <form onSubmit={handleSubmit} className="space-y-3">
                <textarea 
                    placeholder="Paste Full Script Text Here (e.g., Scene headers, action blocks)"
                    value={scriptText}
                    onChange={(e) => setScriptText(e.target.value)}
                    rows="8"
                    required
                    className="w-full p-2 border border-gray-300 rounded focus:ring-purple-500 focus:border-purple-500"
                />
                <textarea 
                    placeholder='Initial Planned Schedule (JSON Format: {"day_1": "Shoot scenes 1-5", ...})'
                    value={plannedSchedule}
                    onChange={(e) => setPlannedSchedule(e.target.value)}
                    rows="3"
                    required
                    className="w-full p-2 border border-gray-300 rounded focus:ring-purple-500 focus:border-purple-500 font-mono text-sm"
                />
                <button 
                    type="submit" 
                    disabled={isLoading || !scriptText || !plannedSchedule}
                    className="w-full bg-purple-600 text-white p-2 rounded font-semibold hover:bg-purple-700 transition duration-150 disabled:opacity-50 flex items-center justify-center"
                >
                    {isLoading ? <LoadingSpinner /> : 'Upload Script & Plan'}
                </button>
            </form>
        </Card>
    );
};

// --- Component 3: Schedule Display and Generation ---

const ScheduleManager = ({ onLog }) => {
    const [dayNumber, setDayNumber] = useState(1);
    const [scheduleData, setScheduleData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const generateSchedule = useCallback(async (e) => {
        if (e) e.preventDefault();
        setIsLoading(true);
        setScheduleData(null);
        onLog('loading', `Generating AI schedule for Day ${dayNumber}... This uses the Gemini model.`);

        const payload = {
            project_id: DEMO_PROJECT_ID,
            day_number: dayNumber,
        };

        try {
            // 1. Generate the schedule
            let response = await fetch(`${API_BASE_URL}/schedule/generate/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            let result = await response.json();

            if (!response.ok) {
                // If generation fails (e.g., due to AI parsing error), try fetching history
                throw new Error(result.detail || 'Schedule generation failed.');
            }
            
            // 2. Fetch the saved schedule history (for plan comparison)
            response = await fetch(`${API_BASE_URL}/schedule/history/${DEMO_PROJECT_ID}/${dayNumber}`);
            result = await response.json();
            
            if (!response.ok) {
                 throw new Error(result.detail || 'Failed to fetch historical schedule for comparison.');
            }

            setScheduleData(result);
            onLog('success', `AI Schedule generated and loaded for Day ${dayNumber}. Current production delay: ${result.delay_hours} hours.`);

        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred during scheduling.');
        } finally {
            setIsLoading(false);
        }
    }, [dayNumber, onLog]);
    
    // Renders the Comparison Graphs/Schedule view
    const ScheduleView = ({ data }) => {
        const teams = Object.keys(data.schedules);

        return (
            <div className="mt-6 border-t pt-4">
                <h3 className="text-xl font-bold text-blue-700 mb-4">Daily Schedule (Day {data.day_number})</h3>
                <div className="bg-blue-50 p-4 rounded-lg border-l-4 border-blue-400 mb-6">
                    <p className="font-semibold text-sm">Initial Planned Focus:</p>
                    <p className="text-blue-800 italic">{data.initial_planned_focus}</p>
                    <p className="font-semibold text-sm mt-2">Current Delay:</p>
                    <p className="text-red-600 font-bold">{data.delay_hours} hours behind schedule.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                    {teams.map((teamName) => (
                        <div key={teamName} className="bg-gray-50 p-4 rounded-lg border-t-4 border-gray-400 shadow-sm">
                            <h4 className="text-lg font-bold text-gray-800 mb-3">{teamName}</h4>
                            <ul className="space-y-2">
                                {data.schedules[teamName].map((task, idx) => (
                                    <li key={idx} className="flex space-x-2 text-sm">
                                        <span className="font-mono text-gray-600 w-1/4 min-w-[80px] font-semibold">{task.time}</span>
                                        <span className="w-3/4">{task.task}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </div>
        );
    };


    return (
        <Card title="3. Generate & View Daily Schedules" className="lg:col-span-3">
            <form onSubmit={generateSchedule} className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-4 mb-4">
                <input 
                    type="number" 
                    placeholder="Shoot Day Number"
                    value={dayNumber}
                    onChange={(e) => setDayNumber(Number(e.target.value))}
                    min="1"
                    required
                    className="p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500 flex-grow"
                />
                <button 
                    type="submit" 
                    disabled={isLoading || dayNumber < 1}
                    className="bg-blue-600 text-white p-2 rounded font-semibold hover:bg-blue-700 transition duration-150 disabled:opacity-50 flex items-center justify-center min-w-[200px]"
                >
                    {isLoading ? <LoadingSpinner /> : `Generate Schedule for Day ${dayNumber}`}
                </button>
            </form>

            {scheduleData && <ScheduleView data={scheduleData} />}
        </Card>
    );
};

// --- Main Application Component ---
const App = () => {
    const [status, setStatus] = useState({ status: 'info', message: `Project ID: ${DEMO_PROJECT_ID}. Backend: ${API_BASE_URL}` });

    const handleLog = (type, message) => {
        setStatus({ status: type, message: message });
    };

    return (
        <div className="min-h-screen bg-gray-50 p-4 sm:p-8">
            <header className="mb-8 max-w-6xl mx-auto">
                <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 text-center">
                    AI Production Scheduler
                </h1>
                <p className="text-center text-gray-500 mt-1">
                    Input teams and script to generate a delay-adjusted daily schedule.
                </p>
            </header>

            <main className="max-w-6xl mx-auto">
                <StatusMessage status={status.status} message={status.message} />
                
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <TeamInputForm onLog={handleLog} />
                    <ScriptInputForm onLog={handleLog} />
                </div>

                <div className="mt-6">
                    <ScheduleManager onLog={handleLog} />
                </div>
                
                {/* FOR TESTING: Simple form to update the delay status */}
                <Card title="4. Debug: Update Delay (Manual Input)" className="mt-6">
                    <DelayUpdaterForm onLog={handleLog} />
                </Card>
            </main>
        </div>
    );
};

// Helper component for manual delay updating (for testing the AI's response)
const DelayUpdaterForm = ({ onLog }) => {
    const [delayHours, setDelayHours] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    
    const handleUpdate = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', `Updating cumulative delay to ${delayHours} hours...`);
        
        const formData = new FormData();
        formData.append('project_id', DEMO_PROJECT_ID);
        formData.append('cumulative_delay_hours', delayHours);

        try {
            const response = await fetch(`${API_BASE_URL}/status/update/`, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Failed to update status.');

            onLog('success', result.message);
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <form onSubmit={handleUpdate} className="flex space-x-4">
            <input 
                type="number" 
                placeholder="Cumulative Delay Hours"
                value={delayHours}
                onChange={(e) => setDelayHours(Number(e.target.value))}
                min="0"
                required
                className="p-2 border border-gray-300 rounded focus:ring-red-500 focus:border-red-500 flex-grow"
            />
            <button 
                type="submit" 
                disabled={isLoading}
                className="bg-red-600 text-white p-2 rounded font-semibold hover:bg-red-700 transition duration-150 disabled:opacity-50 flex items-center justify-center min-w-[150px]"
            >
                {isLoading ? <LoadingSpinner /> : 'Update Delay'}
            </button>
        </form>
    );
};


export default App;