import React, { useState, useEffect, useCallback } from 'react';

// Base URL for the Python FastAPI server.
const API_BASE_URL = "http://localhost:8000";

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
// Allows marking a person as a lead and associates them with a role
const PersonnelForm = ({ onLog, onAdded }) => {
    const [name, setName] = useState('');
    const [role, setRole] = useState('');
    const [leaderName, setLeaderName] = useState('');
    const [isLead, setIsLead] = useState(false);
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
        // Keep old backend compatibility but also include a flag
        formData.append('is_lead', isLead ? 'true' : 'false');

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
            setIsLead(false);
            if (onAdded) onAdded();
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

                <label className="flex items-center space-x-2 text-sm">
                    <input type="checkbox" checked={isLead} onChange={(e) => setIsLead(e.target.checked)} className="h-4 w-4" />
                    <span>Mark as Role Lead</span>
                </label>

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

// --- Component: DynamicItemRow ---
const DynamicItemRow = ({ item, idx, onChange, onRemove }) => {
    return (
        <div className="grid grid-cols-12 gap-2 items-end p-2 border rounded-lg">
            <input
                className="col-span-5 p-2 border rounded"
                placeholder="Item name"
                value={item.name}
                onChange={(e) => onChange(idx, { ...item, name: e.target.value })}
                required
            />
            <input
                className="col-span-2 p-2 border rounded"
                placeholder="Qty"
                type="number"
                min="1"
                value={item.quantity}
                onChange={(e) => onChange(idx, { ...item, quantity: Number(e.target.value) })}
                required
            />
            <input
                className="col-span-2 p-2 border rounded"
                placeholder="Unit Cost"
                type="number"
                min="0"
                step="0.01"
                value={item.unit_cost}
                onChange={(e) => onChange(idx, { ...item, unit_cost: Number(e.target.value) })}
                required
            />
            <input
                className="col-span-2 p-2 border rounded"
                placeholder="Hour (HH:MM)"
                value={item.hour}
                onChange={(e) => onChange(idx, { ...item, hour: e.target.value })}
            />
            <div className="col-span-1 flex space-x-2">
                <select
                    value={item.action}
                    onChange={(e) => onChange(idx, { ...item, action: e.target.value })}
                    className="p-2 border rounded w-full"
                >
                    <option value="store">Store</option>
                    <option value="repair">Repair</option>
                    <option value="discard">Discard</option>
                    <option value="use">Use</option>
                    <option value="other">Other</option>
                </select>
                <button type="button" onClick={() => onRemove(idx)} className="text-red-600 font-semibold">Remove</button>
            </div>
        </div>
    );
};

// --- Component: Item Collection Form (2) ---
// Now supports multiple items with unit cost, quantity, hour, and an action to be taken.
const ItemCollectionForm = ({ onLog }) => {
    const [date, setDate] = useState(getTodayDate());
    const [items, setItems] = useState([{ name: '', quantity: 1, unit_cost: 0.0, hour: '', action: 'store', lead_name: '' }]);
    const [reporterName, setReporterName] = useState('');
    const [notes, setNotes] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const addRow = () => setItems(prev => [...prev, { name: '', quantity: 1, unit_cost: 0.0, hour: '', action: 'store', lead_name: '' }]);
    const removeRow = (idx) => setItems(prev => prev.filter((_, i) => i !== idx));
    const updateRow = (idx, newItem) => setItems(prev => prev.map((it, i) => i === idx ? newItem : it));

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Logging item collection (detailed)...');

        // Build structured JSON payload - backend will need to support this route
        const payload = {
            project_id: DEMO_PROJECT_ID,
            report_date: date,
            reporter_name: reporterName,
            notes: notes,
            items: items.map(it => ({
                name: it.name,
                quantity: Number(it.quantity) || 1,
                unit_cost: Number(it.unit_cost) || 0,
                hour: it.hour || null,
                action: it.action || 'store',
                lead_name: it.lead_name || null
            }))
        };

        try {
            const response = await fetch(`${API_BASE_URL}/items/log/extended/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Failed to log collected items.');

            onLog('success', result.message);
            setItems([{ name: '', quantity: 1, unit_cost: 0.0, hour: '', action: 'store', lead_name: '' }]);
            setNotes('');
            setReporterName('');
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="2. Log Item Collection (Detailed)">
            <form onSubmit={handleSubmit} className="space-y-4">
                <input 
                    type="date" 
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                />

                <div className="space-y-3">
                    {items.map((it, idx) => (
                        <div key={idx}>
                            <DynamicItemRow item={it} idx={idx} onChange={updateRow} onRemove={removeRow} />
                            <input
                                className="w-full p-2 border rounded mt-2"
                                placeholder="Lead for this item (optional)"
                                value={it.lead_name}
                                onChange={(e) => updateRow(idx, { ...it, lead_name: e.target.value })}
                            />
                        </div>
                    ))}
                    <div className="flex justify-end">
                        <button type="button" onClick={addRow} className="text-indigo-600 font-semibold">+ Add Item</button>
                    </div>
                </div>

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
                    {isLoading ? 'Logging...' : 'Log Collected Items (Detailed)'}
                </button>
            </form>
        </Card>
    );
};

// --- Component: Resources Form (3) ---
// Extended to accept cost per resource and lead for the resource checkout
const ResourcesForm = ({ onLog }) => {
    const [date, setDate] = useState(getTodayDate());
    const [type, setType] = useState('Equipment');
    const [itemName, setItemName] = useState('');
    const [quantity, setQuantity] = useState(1);
    const [unitCost, setUnitCost] = useState(0);
    const [notes, setNotes] = useState('');
    const [reporterName, setReporterName] = useState('');
    const [leadName, setLeadName] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Logging resource usage...');

        const payload = {
            project_id: DEMO_PROJECT_ID,
            report_date: date,
            resource_type: type,
            item_name: itemName,
            quantity: Number(quantity) || 1,
            unit_cost: Number(unitCost) || 0,
            reporter_name: reporterName,
            lead_name: leadName,
            notes: notes
        };

        try {
            const response = await fetch(`${API_BASE_URL}/resources/log/extended/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Failed to log resource.');

            onLog('success', result.message);
            setItemName('');
            setNotes('');
            setQuantity(1);
            setUnitCost(0);
            setReporterName('');
            setLeadName('');
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="3. Log Resource Usage (with cost)">
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
                    type="number" 
                    placeholder="Unit Cost (per item)"
                    value={unitCost}
                    onChange={(e) => setUnitCost(e.target.value)}
                    min="0"
                    step="0.01"
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                />
                 <input 
                    type="text" 
                    placeholder="Lead for this checkout (optional)"
                    value={leadName}
                    onChange={(e) => setLeadName(e.target.value)}
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
// Now supports dynamic employee rows to track presence, wage, and food cost per employee
const AttendanceForm = ({ onLog }) => {
    const [date, setDate] = useState(getTodayDate());
    const [rows, setRows] = useState([{ name: '', present: true, wage: 0, food_cost: 0 }]);
    const [reporterName, setReporterName] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const addRow = () => setRows(prev => [...prev, { name: '', present: true, wage: 0, food_cost: 0 }]);
    const removeRow = (idx) => setRows(prev => prev.filter((_, i) => i !== idx));
    const updateRow = (idx, newRow) => setRows(prev => prev.map((r, i) => i === idx ? newRow : r));

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        onLog('loading', 'Logging attendance (detailed)...');

        // Prepare arrays for compatibility and a structured payload
        const present_names = rows.filter(r => r.present).map(r => r.name).filter(Boolean);
        const absent_names = rows.filter(r => !r.present).map(r => r.name).filter(Boolean);

        const payload = {
            project_id: DEMO_PROJECT_ID,
            report_date: date,
            reporter_name: reporterName,
            present_entries: rows.filter(r => r.present && r.name).map(r => ({ name: r.name, wage: Number(r.wage)||0, food_cost: Number(r.food_cost)||0 })),
            absent_entries: rows.filter(r => !r.present && r.name).map(r => ({ name: r.name }))
        };

        try {
            const response = await fetch(`${API_BASE_URL}/attendance/log/extended/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Failed to log attendance.');

            onLog('success', result.message);
            setRows([{ name: '', present: true, wage: 0, food_cost: 0 }]);
            setReporterName('');
        } catch (error) {
            onLog('error', error.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card title="4. Log Daily Attendance (Detailed)" className="lg:col-span-3">
            <form onSubmit={handleSubmit} className="space-y-4">
                <input 
                    type="date" 
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                />

                <div className="space-y-2">
                    {rows.map((r, idx) => (
                        <div key={idx} className="grid grid-cols-12 gap-2 items-end p-2 border rounded-lg">
                            <input className="col-span-4 p-2 border rounded" placeholder="Employee Name" value={r.name} onChange={(e) => updateRow(idx, { ...r, name: e.target.value })} required />
                            <label className="col-span-2 flex items-center space-x-2">
                                <input type="checkbox" checked={r.present} onChange={(e) => updateRow(idx, { ...r, present: e.target.checked })} className="h-4 w-4" />
                                <span>Present</span>
                            </label>
                            <input className="col-span-3 p-2 border rounded" placeholder="Wage (₹)" type="number" min="0" value={r.wage} onChange={(e) => updateRow(idx, { ...r, wage: e.target.value })} />
                            <input className="col-span-2 p-2 border rounded" placeholder="Food Cost (₹)" type="number" min="0" value={r.food_cost} onChange={(e) => updateRow(idx, { ...r, food_cost: e.target.value })} />
                            <div className="col-span-1 flex justify-end">
                                <button type="button" onClick={() => removeRow(idx)} className="text-red-600 font-semibold">Remove</button>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="flex justify-between">
                    <button type="button" onClick={addRow} className="text-indigo-600 font-semibold">+ Add Employee</button>
                    <input type="text" placeholder="Reporter Name (Head of Dept - Required)" value={reporterName} onChange={(e) => setReporterName(e.target.value)} required className="p-2 border rounded w-1/2" />
                </div>

                <button 
                    type="submit" 
                    disabled={isLoading}
                    className="w-full bg-green-600 text-white p-2 rounded-lg font-semibold hover:bg-green-700 transition duration-150 shadow-md transform hover:scale-[1.01] disabled:opacity-50"
                >
                    {isLoading ? 'Logging...' : 'Submit Attendance Log (Detailed)'}
                </button>
            </form>
        </Card>
    );
};

// --- Component: AI Report Generator (5) ---
// Unchanged except it will still call the existing /report/daily_summary/ endpoint
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
            const response = await fetch(`${API_BASE_URL}/report/daily_summary/${DEMO_PROJECT_ID}/${date}`);
            const result = await response.json();

            if (!response.ok) {
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
    const [refreshKey, setRefreshKey] = useState(0);

    const handleLog = (type, message) => {
        setStatus({ status: type, message: message });
    };

    // refreshKey can be incremented to signal children to re-fetch personnel if later implemented
    const triggerRefresh = () => setRefreshKey(k => k + 1);
    
    useEffect(() => {
        document.title = "AI Production Tracker (React)";
        document.body.className = "bg-gray-50 font-sans"; 
    }, []);

    return (
        <div className="min-h-screen p-4 sm:p-8">
            <header className="mb-8 max-w-6xl mx-auto">
                <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 text-center">
                    AI Production Data Tracker (React) - Detailed
                </h1>
                <p className="text-center text-gray-500 mt-1">
                    Log crew, detailed items with costs/hours, resources with cost, and generate AI summaries.
                </p>
            </header>

            <main className="max-w-6xl mx-auto">
                <StatusMessage status={status.status} message={status.message} />
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <PersonnelForm onLog={handleLog} onAdded={triggerRefresh} />
                    <ItemCollectionForm onLog={handleLog} />
                    <ResourcesForm onLog={handleLog} />
                </div>

                <div className="grid grid-cols-1 mt-6 lg:grid-cols-3 gap-6">
                    <AttendanceForm onLog={handleLog} />
                </div>
                
                <div className="mt-6">
                    <AIReportGenerator onLog={handleLog} />
                </div>
            </main>
        </div>
    );
};

export default App;
