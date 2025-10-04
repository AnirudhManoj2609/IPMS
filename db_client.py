# db_client.py
import asyncpg
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta

class DatabaseClient:
    """
    Client to interact directly with the PostgreSQL database.
    Replaces the SpringBootAPIClient for direct data access.
    """
    def __init__(self):
        # Database connection parameters from environment variables
        self.dsn = os.getenv("DATABASE_URL")
        if not self.dsn:
            print("ERROR: DATABASE_URL environment variable not set.")
        self.pool = None

    async def initialize_pool(self):
        """Initializes the connection pool"""
        if self.dsn and not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()

# ==================== USER DATA ====================
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get complete user profile and role permissions"""
        async with self.pool.acquire() as conn:
            # Join user data and permissions
            query = """
            SELECT 
                u.user_id, u.name, u.preferred_name, u.role, u.department,
                p.production_name, p.production_status
            FROM users u
            JOIN productions p ON u.current_production_id = p.production_id
            WHERE u.user_id = $1
            """
            record = await conn.fetchrow(query, user_id)
            if record:
                return dict(record)
            return None

# ==================== SCHEDULE & CALENDAR ====================
    async def get_schedule(self, user_id: str, date_input: str) -> List[Dict]:
        """Get user's schedule for a specific date/range"""
        target_date = None
        if date_input == 'today':
            target_date = date.today()
        elif date_input == 'tomorrow':
            target_date = date.today() + timedelta(days=1)
        elif date_input == 'this_week':
            # Simplified: Fetches events starting within the next 7 days
            start_date = date.today()
            end_date = start_date + timedelta(days=7)
            query = """
            SELECT event_name, start_time, location 
            FROM events 
            WHERE user_id = $1 AND start_time::date BETWEEN $2 AND $3
            ORDER BY start_time
            """
            async with self.pool.acquire() as conn:
                records = await conn.fetch(query, user_id, start_date, end_date)
                return [dict(r) for r in records]
        else:
            try:
                target_date = datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError:
                return [{"error": "Invalid date format."}]

        if target_date:
            query = """
            SELECT event_name, start_time, location 
            FROM events 
            WHERE user_id = $1 AND start_time::date = $2
            ORDER BY start_time
            """
            async with self.pool.acquire() as conn:
                records = await conn.fetch(query, user_id, target_date)
                return [dict(r) for r in records]
        return []

    async def get_next_call_time(self, user_id: str, production_id: str) -> Optional[Dict]:
        """Get user's next call time"""
        now = datetime.now()
        query = """
        SELECT call_time, location, event_name 
        FROM call_events 
        WHERE user_id = $1 AND production_id = $2 AND call_time > $3
        ORDER BY call_time ASC 
        LIMIT 1
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, user_id, production_id, now)
            return dict(record) if record else None

# ==================== TASKS ====================
    async def get_tasks(self, user_id: str, filter_type: str = 'all') -> List[Dict]:
        """Get user's tasks"""
        where_clause = "WHERE user_id = $1 "
        params: List[Any] = [user_id]
        
        if filter_type.lower() == 'today':
            where_clause += "AND due_date::date = CURRENT_DATE "
        elif filter_type.lower() == 'overdue':
            where_clause += "AND due_date < CURRENT_DATE AND status != 'completed' "
        elif filter_type.lower() == 'completed':
            where_clause += "AND status = 'completed' "
        else: # 'all' or 'pending'
            where_clause += "AND status != 'completed' "

        query = f"SELECT task_id, description, due_date, status FROM tasks {where_clause} ORDER BY due_date ASC"
        
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, *params)
            return [dict(r) for r in records]

    async def complete_task(self, task_id: str, user_id: str) -> bool:
        """Mark a task as complete"""
        query = "UPDATE tasks SET status = 'completed', completed_at = $1 WHERE task_id = $2 AND user_id = $3"
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, datetime.now(), task_id, user_id)
            return result == "UPDATE 1"

# ... (Add other database methods like get_timesheet_status, search_crew, etc., following this pattern) ...

    async def get_timesheet_status(self, user_id: str) -> Optional[Dict]:
        """Get timesheet status for the current week"""
        # Finds the last submitted timesheet for the current calendar week
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        query = """
        SELECT status, total_hours 
        FROM timesheets 
        WHERE user_id = $1 AND week_start = $2
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, user_id, week_start)
            return dict(record) if record else {"status": "not submitted", "total_hours": 0}

    async def search_crew(self, production_id: str, query: str) -> List[Dict]:
        """Search for crew members by name or role"""
        search_term = f"%{query.lower()}%"
        query_sql = """
        SELECT name, role, department, phone, email 
        FROM users 
        WHERE current_production_id = $1 AND (LOWER(name) LIKE $2 OR LOWER(role) LIKE $2)
        LIMIT 10
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query_sql, production_id, search_term)
            return [dict(r) for r in records]

    async def get_call_sheet(self, production_id: str, date_input: str) -> Optional[Dict]:
        """Get call sheet for a specific date"""
        target_date = None
        if date_input == 'today':
            target_date = date.today()
        elif date_input == 'tomorrow':
            target_date = date.today() + timedelta(days=1)
        else:
            try:
                target_date = datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError:
                return {"error": "Invalid date format."}

        query = """
        SELECT * FROM call_sheets 
        WHERE production_id = $1 AND shoot_date = $2
        LIMIT 1
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(query, production_id, target_date)
            return dict(record) if record else None
