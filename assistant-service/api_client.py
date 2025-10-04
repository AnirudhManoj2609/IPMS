# api_client.py
"""
API Client to connect Personal Assistant with Spring Boot backend
Fetches real user data, schedules, tasks, etc.
"""

import httpx
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import json


class SpringBootAPIClient:
    """
    Client to interact with Spring Boot backend
    Handles authentication and data fetching
    """
    
    def __init__(self, base_url: str = None, auth_token: str = None):
        self.base_url = base_url or os.getenv("SPRING_BOOT_API_URL", "http://localhost:8080/api")
        self.auth_token = auth_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}" if auth_token else ""
        }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    # ==================== USER DATA ====================
    
    async def get_user_profile(self, user_id: str) -> Dict:
        """Get complete user profile"""
        try:
            response = await self.client.get(
                f"{self.base_url}/users/{user_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching user profile: {e}")
            return {}
    
    async def get_user_role_permissions(self, user_id: str) -> Dict:
        """Get user's role and permissions"""
        try:
            response = await self.client.get(
                f"{self.base_url}/users/{user_id}/permissions",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching permissions: {e}")
            return {}
    
    # ==================== SCHEDULE & CALENDAR ====================
    
    async def get_schedule(self, user_id: str, date_input: str) -> List[Dict]:
        """
        Get user's schedule for a specific date/range
        date_input: 'today', 'tomorrow', 'this_week', or 'YYYY-MM-DD'
        """
        try:
            # Parse date input
            if date_input == 'today':
                target_date = date.today().isoformat()
            elif date_input == 'tomorrow':
                target_date = (date.today() + timedelta(days=1)).isoformat()
            elif date_input == 'this_week':
                # Get range for this week
                response = await self.client.get(
                    f"{self.base_url}/schedule/{user_id}/week",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            else:
                target_date = date_input
            
            response = await self.client.get(
                f"{self.base_url}/schedule/{user_id}/date/{target_date}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return []
    
    async def get_next_call_time(self, user_id: str, production_id: str) -> Optional[Dict]:
        """Get user's next call time"""
        try:
            response = await self.client.get(
                f"{self.base_url}/schedule/{user_id}/next-call",
                params={"productionId": production_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching next call time: {e}")
            return None
    
    async def get_call_sheet(self, production_id: str, date_input: str) -> Dict:
        """Get call sheet for a specific date"""
        try:
            if date_input == 'today':
                target_date = date.today().isoformat()
            elif date_input == 'tomorrow':
                target_date = (date.today() + timedelta(days=1)).isoformat()
            else:
                target_date = date_input
            
            response = await self.client.get(
                f"{self.base_url}/productions/{production_id}/call-sheet/{target_date}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching call sheet: {e}")
            return {}
    
    # ==================== TASKS ====================
    
    async def get_tasks(self, user_id: str, filter_type: str = 'all') -> List[Dict]:
        """
        Get user's tasks
        filter_type: 'all', 'today', 'overdue', 'completed', 'pending'
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/tasks/user/{user_id}",
                params={"filter": filter_type},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []
    
    async def complete_task(self, task_id: str, user_id: str) -> bool:
        """Mark a task as complete"""
        try:
            response = await self.client.put(
                f"{self.base_url}/tasks/{task_id}/complete",
                json={"userId": user_id, "completedAt": datetime.now().isoformat()},
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error completing task: {e}")
            return False
    
    async def create_task(self, user_id: str, task_data: Dict) -> Optional[Dict]:
        """Create a new task"""
        try:
            response = await self.client.post(
                f"{self.base_url}/tasks",
                json={**task_data, "userId": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating task: {e}")
            return None
    
    # ==================== TIMESHEETS ====================
    
    async def get_timesheet_status(self, user_id: str, week_start: str = None) -> Dict:
        """Get timesheet status for current or specific week"""
        try:
            params = {}
            if week_start:
                params['weekStart'] = week_start
            
            response = await self.client.get(
                f"{self.base_url}/timesheets/user/{user_id}/status",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching timesheet: {e}")
            return {"status": "error", "message": str(e)}
    
    async def submit_timesheet_entry(self, user_id: str, entry_data: Dict) -> bool:
        """Submit a timesheet entry"""
        try:
            response = await self.client.post(
                f"{self.base_url}/timesheets/user/{user_id}/entries",
                json=entry_data,
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error submitting timesheet: {e}")
            return False
    
    # ==================== CREW & CONTACTS ====================
    
    async def search_crew(self, production_id: str, query: str) -> List[Dict]:
        """Search for crew members by name or role"""
        try:
            response = await self.client.get(
                f"{self.base_url}/productions/{production_id}/crew/search",
                params={"q": query},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error searching crew: {e}")
            return []
    
    async def get_department_crew(self, production_id: str, department: str) -> List[Dict]:
        """Get all crew members in a department"""
        try:
            response = await self.client.get(
                f"{self.base_url}/productions/{production_id}/departments/{department}/crew",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching department crew: {e}")
            return []
    
    # ==================== PRODUCTION DATA ====================
    
    async def get_production_status(self, production_id: str) -> Dict:
        """Get current production status and metrics"""
        try:
            response = await self.client.get(
                f"{self.base_url}/productions/{production_id}/status",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching production status: {e}")
            return {}
    
    async def get_budget_info(self, production_id: str, user_id: str) -> Optional[Dict]:
        """Get budget information (if user has permission)"""
        try:
            response = await self.client.get(
                f"{self.base_url}/productions/{production_id}/budget",
                params={"requesterId": user_id},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching budget: {e}")
            return None
    
    async def get_shooting_schedule(self, production_id: str) -> Dict:
        """Get the shooting schedule"""
        try:
            response = await self.client.get(
                f"{self.base_url}/productions/{production_id}/shooting-schedule",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching shooting schedule: {e}")
            return {}
    
    # ==================== LOCATIONS ====================
    
    async def get_location_info(self, location_id: str) -> Dict:
        """Get location details"""
        try:
            response = await self.client.get(
                f"{self.base_url}/locations/{location_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching location: {e}")
            return {}
    
    # ==================== DOCUMENTS & REPORTS ====================
    
    async def get_recent_documents(self, production_id: str, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent documents user has access to"""
        try:
            response = await self.client.get(
                f"{self.base_url}/documents/production/{production_id}",
                params={"userId": user_id, "limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching documents: {e}")
            return []
    
    # ==================== NOTIFICATIONS ====================
    
    async def get_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict]:
        """Get user notifications"""
        try:
            response = await self.client.get(
                f"{self.base_url}/notifications/user/{user_id}",
                params={"unreadOnly": unread_only},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            return []
    
    async def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            response = await self.client.put(
                f"{self.base_url}/notifications/{notification_id}/read",
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error marking notification: {e}")
            return False
    
    # ==================== USER PREFERENCES ====================
    
    async def get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences"""
        try:
            response = await self.client.get(
                f"{self.base_url}/users/{user_id}/preferences",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching preferences: {e}")
            return {}
    
    async def update_user_preference(self, user_id: str, key: str, value: Any) -> bool:
        """Update a user preference"""
        try:
            response = await self.client.put(
                f"{self.base_url}/users/{user_id}/preferences",
                json={"key": key, "value": value},
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error updating preference: {e}")
            return False


# Singleton instance manager
class APIClientManager:
    """
    Manages API client instances per user
    Handles token refresh and connection pooling
    """
    
    _clients: Dict[str, SpringBootAPIClient] = {}
    
    @classmethod
    def get_client(cls, user_id: str, auth_token: str) -> SpringBootAPIClient:
        """Get or create API client for user"""
        if user_id not in cls._clients:
            cls._clients[user_id] = SpringBootAPIClient(auth_token=auth_token)
        return cls._clients[user_id]
    
    @classmethod
    async def close_client(cls, user_id: str):
        """Close and remove client"""
        if user_id in cls._clients:
            await cls._clients[user_id].close()
            del cls._clients[user_id]
    
    @classmethod
    async def close_all(cls):
        """Close all clients"""
        for client in cls._clients.values():
            await client.close()
        cls._clients.clear()


from datetime import timedelta