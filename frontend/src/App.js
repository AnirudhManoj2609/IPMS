import React, { useState, useEffect, useCallback } from 'react';

// Base URL for the Python FastAPI server.
const API_BASE_URL = window.location.origin;

// Project ID constant
const DEMO_PROJECT_ID = "PROD-EPIC-2025";

// Utility function to get today's date in YYYY-MM-DD format
const getTodayDate = () => new Date().toISOString().slice(0, 10);

// --- Component: Card Wrapper ---
const Card = ({ title, children, className = '' }) => (
    <div className={`bg-white p-6 rounded-xl shadow-lg border border-gray-100 ${className}`}>
        <h2 className="text-xl font-bold text-gray-800 mb-4 border-b pb-2">{title}</h2>
        {children}
    </div>
);

// --- Component: Status Message ---
const StatusMessage = ({ status, message }) => {
    if (!message) return null;
    let style = "bg-blue-100 text-blue-700";
    if (status === 'success') style = "bg-green-100 text-green-700";
    if (status === 'error') style = "bg-red-100 text-red-700";
    if (status === 'warning' || status === 'loading') style = "bg-yellow-100 text-yellow-700";

    return (
        <div className={`p-3 rounded-lg font-medium text-sm my-3 ${style}`} role="alert">
            {message}
        </div>
    );
};

// --- Component: Personnel Form (1) ---
const PersonnelForm = ({ onLog }) => {
    const [name, setName] = useState('');
    const [role, setRole] = useState('');
    const [leaderName, setLeaderName] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Adding personnel...');
        
        const formData = new FormData();
        formData.append('project_id', DEMO_PROJECT_ID);
        formData.append('name', name);
        formData.append('role', role);
        if (leaderName) formData.append('leader_name', leaderName);

        try {
            const response = await fetch(`${API_BASE_URL}/personnel/add/`, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to add personnel.');
            }

            onLog('success', result.message);
            setName('');
            setRole('');
            setLeaderName('');
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="1. Add Crew Member">
            <form onSubmit={handleSubmit} className="space-y-4">
                <input 
                    type="text" 
                    placeholder="Crew Member Name (e.g., Jane Doe)"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                />
                <input 
                    type="text" 
                    placeholder="Role (e.g., Gaffer, Camera Op)"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                />
                 <input 
                    type="text" 
                    placeholder="Reporting Leader (Optional)"
                    value={leaderName}
                    onChange={(e) => setLeaderName(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="w-full bg-indigo-600 text-white p-2 rounded-lg font-semibold hover:bg-indigo-700 transition duration-150 shadow-md transform hover:scale-[1.01] disabled:opacity-50"
                >
                    {isLoading ? 'Adding...' : 'Add Personnel'}
                </button>
            </form>
        </Card>
    );
};

// --- Component: Item Collection Form (2) ---
const ItemCollectionForm = ({ onLog }) => {
    const [date, setDate] = useState(getTodayDate());
    const [itemNames, setItemNames] = useState('');
    const [reporterName, setReporterName] = useState('');
    const [notes, setNotes] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Logging item collection...');
        
        // Convert comma-separated strings to arrays of item names
        const itemArray = itemNames.split(',').map(n => n.trim()).filter(n => n.length > 0);

        const formData = new FormData();
        formData.append('project_id', DEMO_PROJECT_ID);
        formData.append('report_date', date);
        formData.append('reporter_name', reporterName); // Reporter is mandatory
        if (notes) formData.append('notes', notes);

        // Append lists of names as multiple entries
        itemArray.forEach(name => formData.append('item_names', name));

        try {
            // NOTE: This assumes a new backend endpoint /items/log/ exists
            const response = await fetch(`${API_BASE_URL}/items/log/`, { 
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to log collected items.');
            }

            onLog('success', result.message);
            setItemNames('');
            setNotes('');
            setReporterName('');
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="2. Log Item Collection">
            <form onSubmit={handleSubmit} className="space-y-4">
                <input 
                    type="date" 
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                />
                <textarea 
                    placeholder="Items Collected/Used (Comma-separated, e.g., 'Antique Vase', 'New Signage')"
                    value={itemNames}
                    onChange={(e) => setItemNames(e.target.value)}
                    rows="2"
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                />
                <input 
                    type="text" 
                    placeholder="Reporter Name (Head of Dept)"
                    value={reporterName}
                    onChange={(e) => setReporterName(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                />
                <textarea 
                    placeholder="Notes (Optional: Storage Location, Condition)"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows="2"
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                />
                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="w-full bg-purple-600 text-white p-2 rounded-lg font-semibold hover:bg-purple-700 transition duration-150 shadow-md transform hover:scale-[1.01] disabled:opacity-50"
                >
                    {isLoading ? 'Logging...' : 'Log Collected Items'}
                </button>
            </form>
        </Card>
    );
};

// --- Component: Resources Form (3) ---
const ResourcesForm = ({ onLog }) => {
    const [date, setDate] = useState(getTodayDate());
    const [type, setType] = useState('Equipment');
    const [itemName, setItemName] = useState('');
    const [quantity, setQuantity] = useState(1);
    const [notes, setNotes] = useState('');
    const [reporterName, setReporterName] = useState(''); // NEW: Reporter name for enforcement
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Logging resource usage...');
        
        const formData = new FormData();
        formData.append('project_id', DEMO_PROJECT_ID);
        formData.append('report_date', date);
        formData.append('resource_type', type);
        formData.append('item_name', itemName);
        formData.append('quantity', quantity.toString());
        formData.append('reporter_name', reporterName); // NEW: Add reporter name
        if (notes) formData.append('notes', notes);

        try {
            const response = await fetch(`${API_BASE_URL}/resources/log/`, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to log resource.');
            }

            onLog('success', result.message);
            setItemName('');
            setNotes('');
            setQuantity(1);
            setReporterName(''); // Clear on success
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="3. Log Resource Usage">
            <form onSubmit={handleSubmit} className="space-y-4">
                <input 
                    type="date" 
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                />
                <select 
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                >
                    <option value="Equipment">Equipment</option>
                    <option value="Prop">Prop</option>
                    <option value="Location">Location Area</option>
                    <option value="Vehicle">Vehicle</option>
                </select>
                <input 
                    type="text" 
                    placeholder="Item Name (e.g., Main Camera Body 1)"
                    value={itemName}
                    onChange={(e) => setItemName(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                />
                 <input 
                    type="number" 
                    placeholder="Quantity"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    min="1"
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                />
                 <input 
                    type="text" 
                    placeholder="Reporter Name (Head of Dept)"
                    value={reporterName}
                    onChange={(e) => setReporterName(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                />
                <textarea 
                    placeholder="Notes (Optional: Damage, Issue, Location)"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows="2"
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                />
                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="w-full bg-yellow-600 text-white p-2 rounded-lg font-semibold hover:bg-yellow-700 transition duration-150 shadow-md transform hover:scale-[1.01] disabled:opacity-50"
                >
                    {isLoading ? 'Logging...' : 'Log Resource Usage'}
                </button>
            </form>
        </Card>
    );
};

// --- Component: Attendance Form (4) ---
// Note: This form already contained the reporterName field, reinforcing role-based reporting.
const AttendanceForm = ({ onLog }) => {
    const [date, setDate] = useState(getTodayDate());
    const [presentNames, setPresentNames] = useState('');
    const [absentNames, setAbsentNames] = useState('');
    const [reporterName, setReporterName] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Logging attendance...');
        
        // Convert comma-separated strings to arrays of names
        const presentArray = presentNames.split(',').map(n => n.trim()).filter(n => n.length > 0);
        const absentArray = absentNames.split(',').map(n => n.trim()).filter(n => n.length > 0);

        const formData = new FormData();
        formData.append('project_id', DEMO_PROJECT_ID);
        formData.append('report_date', date);
        formData.append('reporter_name', reporterName);
        
        presentArray.forEach(name => formData.append('present_names', name));
        absentArray.forEach(name => formData.append('absent_names', name));
        
        try {
            const response = await fetch(`${API_BASE_URL}/attendance/log/`, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to log attendance.');
            }

            onLog('success', result.message);
            setPresentNames('');
            setAbsentNames('');
            // NOTE: Keeping reporterName populated for consecutive daily logs
            // If you want to clear it, uncomment: setReporterName(''); 
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="4. Log Daily Attendance" className="lg:col-span-3">
            <form onSubmit={handleSubmit} className="space-y-4">
                <input 
                    type="date" 
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                />
                <textarea 
                    placeholder="Present Names (Comma-separated, e.g., Jane, Alex, Chris)"
                    value={presentNames}
                    onChange={(e) => setPresentNames(e.target.value)}
                    rows="2"
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                />
                <textarea 
                    placeholder="Absent Names (Comma-separated)"
                    value={absentNames}
                    onChange={(e) => setAbsentNames(e.target.value)}
                    rows="2"
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                />
                <input 
                    type="text" 
                    placeholder="Reporter Name (Head of Dept - Required)"
                    value={reporterName}
                    onChange={(e) => setReporterName(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                />
                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="w-full bg-green-600 text-white p-2 rounded-lg font-semibold hover:bg-green-700 transition duration-150 shadow-md transform hover:scale-[1.01] disabled:opacity-50"
                >
                    {isLoading ? 'Logging...' : 'Submit Attendance Log'}
                </button>
            </form>
        </Card>
    );
};

// --- Component: AI Report Generator (5) ---
const AIReportGenerator = ({ onLog }) => {
    const [date, setDate] = useState(getTodayDate());
    const [report, setReport] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const handleGenerate = useCallback(async (e) => {
        if (e) e.preventDefault();
        setIsLoading(true);
        setReport(null);
        onLog('loading', `Generating AI Summary for ${date}... This may take a moment.`);
        
        try {
            // This endpoint will now rely on data from all four logging forms.
            const response = await fetch(`${API_BASE_URL}/report/daily_summary/${DEMO_PROJECT_ID}/${date}`);

            const result = await response.json();

            if (!response.ok) {
                // Check for 500 error specifically from the backend if data is missing
                const detail = result.detail || 'Failed to generate report.';
                throw new Error(`Report generation failed: ${detail}.`);
            }

            setReport(result);
            onLog('success', `Report for ${date} loaded. Status: ${result.status}`);
        } catch (error) {
            let errorMessage = error.message;
            if (errorMessage.includes("No data logged")) {
                errorMessage = "Report generation failed: No data logged for this date. Ensure all four types of data are logged.";
            }
            onLog('error', errorMessage || 'An unknown error occurred during report generation.');
        } finally {
            setIsLoading(false);
        }
    }, [date, onLog]);

    // Simple loading spinner display in the button
    const LoadingSpinner = () => (
        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
    );


    return (
        <Card title="5. AI Daily Production Summary" className="lg:col-span-3">
            <form onSubmit={handleGenerate} className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-3 mb-4">
                <input 
                    type="date" 
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 flex-grow"
                />
                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="bg-blue-600 text-white p-2 rounded-lg font-semibold hover:bg-blue-700 transition duration-150 shadow-md disabled:bg-gray-400 transform hover:scale-[1.01] flex items-center justify-center min-w-[180px]"
                >
                    {isLoading ? (
                        <>
                            <LoadingSpinner />
                            Processing...
                        </>
                    ) : 'Generate/View Report'}
                </button>
            </form>

            {report && report.report && (
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 whitespace-pre-wrap text-sm shadow-inner">
                    <p className="font-bold text-gray-700 mb-2">Report Status: <span className="text-purple-600 font-mono">{report.status.toUpperCase()}</span></p>
                    {/* Display the AI generated text */}
                    {report.report}
                </div>
            )}
            {report && !report.report && (
                 <p className="text-red-500 p-2 border border-red-200 bg-red-50 rounded-lg text-sm">
                    {report.status}
                </p>
            )}
        </Card>
    );
};


// --- Main Application Component ---
const App = () => {
    const [status, setStatus] = useState({ status: 'info', message: `Welcome! Project ID: ${DEMO_PROJECT_ID}` });

    const handleLog = (type, message) => {
        setStatus({ status: type, message: message });
    };
    
    useEffect(() => {
        document.title = "AI Production Tracker (React)";
        // Apply the base background and font class to the body.
        document.body.className = "bg-gray-50 font-sans"; 
    }, []);

    return (
        <div className="min-h-screen p-4 sm:p-8">
            <header className="mb-8 max-w-6xl mx-auto">
                <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 text-center">
                    AI Production Data Tracker (React)
                </h1>
                <p className="text-center text-gray-500 mt-1">
                    Log crew, items, resources, and generate your <strong className="text-indigo-600">AI-enhanced daily summary</strong>.
                </p>
            </header>

            <main className="max-w-6xl mx-auto">
                <StatusMessage status={status.status} message={status.message} />
                
                {/* Input Forms Row 1: 3 columns on large screens */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <PersonnelForm onLog={handleLog} />
                    <ItemCollectionForm onLog={handleLog} />
                    <ResourcesForm onLog={handleLog} />
                </div>

                {/* Input Form Row 2: Attendance (spans 3 columns on large screens) */}
                <div className="grid grid-cols-1 mt-6 lg:grid-cols-3 gap-6">
                    <AttendanceForm onLog={handleLog} />
                </div>
                
                {/* AI Report Section (spans 3 columns on large screens) */}
                <div className="mt-6">
                    <AIReportGenerator onLog={handleLog} />
                </div>
            </main>
        </div>
    );
};

export default App;
