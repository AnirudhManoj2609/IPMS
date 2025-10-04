# assistant/personal_assistant_integrated.py

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.llms.base import LLM
from langchain.tools import Tool
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime, timedelta
import os
import json
from pydantic import Field
from groq import Groq

# Import the API client
from api_client import SpringBootAPIClient, APIClientManager


class GroqLLM(LLM):
    """Custom LangChain wrapper for Groq API"""
    
    client: Any = Field(default=None, exclude=True)
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.7
    max_tokens: int = 4096
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    @property
    def _llm_type(self) -> str:
        return "groq"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=stop
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling Groq: {str(e)}"
    
    async def _acall(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await asyncio.get_event_loop().run_in_executor(
                executor, self._call, prompt, stop
            )


class PersonalAssistant:
    """
    Personal AI Assistant with full Spring Boot backend integration
    Now fetches REAL data from your production management system
    """
    
    def __init__(
        self,
        user_id: str,
        auth_token: str,
        production_id: str = None,
        llm_provider: str = "groq"
    ):
        self.user_id = user_id
        self.auth_token = auth_token
        self.production_id = production_id
        self.llm_provider = llm_provider
        
        # Initialize API client for Spring Boot backend
        self.api_client = APIClientManager.get_client(user_id, auth_token)
        
        # Initialize LLM
        self.llm = GroqLLM(model="llama-3.3-70b-versatile", temperature=0.7)
        
        # Memory
        self.conversation_memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10
        )
        
        # User profile (will be loaded from API)
        self.user_profile = {}
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create agent
        self.agent = None  # Will be created after profile loads
        
        self.proactive_enabled = True
    
    async def initialize(self):
        """
        Load user profile and initialize agent
        MUST be called after construction
        """
        # Fetch user profile from Spring Boot
        self.user_profile = await self.api_client.get_user_profile(self.user_id)
        
        if not self.user_profile:
            raise Exception(f"Failed to load user profile for {self.user_id}")
        
        # Get role permissions
        permissions = await self.api_client.get_user_role_permissions(self.user_id)
        self.user_profile['permissions'] = permissions
        
        # Get production info if production_id provided
        if self.production_id:
            prod_status = await self.api_client.get_production_status(self.production_id)
            self.user_profile['production_status'] = prod_status
        
        # Now create the agent with loaded profile
        self.agent = self._create_agent()
        
        return self
    
    def _create_agent(self) -> AgentExecutor:
        """Create personalized agent with role-specific prompt"""
        
        system_prompt = self._get_role_prompt()
        
        template = """{system_prompt}

You have access to the following tools:

{tools}

To use a tool, use this EXACT format:
Action: tool_name
Action Input: the input

If you can answer without a tool, respond directly with your answer.

Previous conversation:
{chat_history}

User: {input}
{agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "chat_history", "agent_scratchpad"],
            partial_variables={
                "system_prompt": system_prompt,
                "tools": self._format_tools()
            }
        )
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.conversation_memory,
            verbose=True,
            handle_parsing_errors="Check your output and make sure it conforms!",
            max_iterations=3,
            early_stopping_method="generate",
            return_intermediate_steps=False
        )
    
    def _format_tools(self) -> str:
        """Format tools for prompt"""
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
    
    def _get_role_prompt(self) -> str:
        """Generate role-specific system prompt"""
        
        name = self.user_profile.get('name', 'User')
        role = self.user_profile.get('role', 'Crew')
        department = self.user_profile.get('department', 'N/A')
        production_name = self.user_profile.get('productionName', 'current production')
        
        return f"""You are a personal AI assistant for {name}, a {role} in the {department} department working on "{production_name}".

Your personality:
- Friendly, professional, and efficient
- Proactive - anticipate needs
- Conversational but respectful
- Film crew communication style

Your responsibilities:
1. Manage schedule and tasks
2. Answer production questions
3. Remind about deadlines and call times
4. Assist with admin tasks
5. Provide role-relevant information
6. Learn preferences and adapt

Current context:
- Role: {role}
- Department: {department}
- Time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}
- Production: {production_name}

You have access to REAL data from the production management system. Use the tools to fetch accurate, up-to-date information."""
    
    def _initialize_tools(self) -> List[Tool]:
        """Initialize tools connected to Spring Boot API"""
        
        return [
            # Schedule & Calendar
            Tool(
                name="get_my_schedule",
                func=lambda date: asyncio.run(self.get_my_schedule(date)),
                description="Get user's schedule. Input: 'today', 'tomorrow', 'this_week', or 'YYYY-MM-DD'"
            ),
            Tool(
                name="get_next_call_time",
                func=lambda x: asyncio.run(self.get_next_call_time()),
                description="Get user's next call time. Input: 'none' or empty"
            ),
            Tool(
                name="get_call_sheet",
                func=lambda date: asyncio.run(self.get_call_sheet(date)),
                description="Get call sheet. Input: 'today', 'tomorrow', or 'YYYY-MM-DD'"
            ),
            
            # Tasks
            Tool(
                name="get_my_tasks",
                func=lambda filter: asyncio.run(self.get_my_tasks(filter)),
                description="Get tasks. Input: 'all', 'today', 'overdue', 'completed'"
            ),
            Tool(
                name="complete_task",
                func=lambda task_id: asyncio.run(self.complete_task(task_id)),
                description="Complete a task. Input: task_id"
            ),
            
            # Timesheets
            Tool(
                name="get_timesheet_status",
                func=lambda x: asyncio.run(self.get_timesheet_status()),
                description="Get timesheet status. Input: 'none' or empty"
            ),
            
            # Crew & Contacts
            Tool(
                name="search_crew",
                func=lambda query: asyncio.run(self.search_crew(query)),
                description="Find crew member. Input: name or role"
            ),
            
            # Production Info
            Tool(
                name="get_production_status",
                func=lambda x: asyncio.run(self.get_production_status()),
                description="Get production status. Input: 'none' or empty"
            ),
            
            # Notifications
            Tool(
                name="get_notifications",
                func=lambda x: asyncio.run(self.get_notifications()),
                description="Get unread notifications. Input: 'none' or empty"
            ),
        ]
    
    # ==================== TOOL IMPLEMENTATIONS (Connected to Spring Boot) ====================
    
    async def get_my_schedule(self, date_input: str) -> str:
        """Get user's schedule from Spring Boot API"""
        try:
            schedule = await self.api_client.get_schedule(self.user_id, date_input)
            
            if not schedule:
                return f"No schedule found for {date_input}"
            
            # Format nicely
            result = f"📅 Schedule for {date_input}:\n\n"
            for item in schedule:
                start = item.get('startTime', 'TBD')
                end = item.get('endTime', 'TBD')
                title = item.get('title', 'Untitled')
                location = item.get('location', 'TBD')
                result += f"• {start} - {end}: {title}\n  Location: {location}\n\n"
            
            return result
        except Exception as e:
            return f"Error fetching schedule: {str(e)}"
    
    async def get_next_call_time(self) -> str:
        """Get user's next call time from Spring Boot API"""
        try:
            call_info = await self.api_client.get_next_call_time(
                self.user_id, 
                self.production_id
            )
            
            if not call_info:
                return "No upcoming call time found"
            
            call_time = datetime.fromisoformat(call_info['callTime'])
            location = call_info.get('location', 'TBD')
            scene = call_info.get('sceneInfo', '')
            
            # Calculate time until
            hours_until = (call_time - datetime.now()).total_seconds() / 3600
            
            result = f"🎬 Next call time:\n"
            result += f"📅 {call_time.strftime('%A, %B %d at %-I:%M %p')}\n"
            result += f"📍 Location: {location}\n"
            if scene:
                result += f"🎥 Scene: {scene}\n"
            result += f"⏰ That's in {hours_until:.1f} hours"
            
            return result
        except Exception as e:
            return f"Error fetching call time: {str(e)}"
    
    async def get_call_sheet(self, date_input: str) -> str:
        """Get call sheet from Spring Boot API"""
        try:
            call_sheet = await self.api_client.get_call_sheet(
                self.production_id,
                date_input
            )
            
            if not call_sheet:
                return f"No call sheet available for {date_input}"
            
            result = f"📋 Call Sheet - {date_input}\n\n"
            result += f"🎬 Production: {call_sheet.get('productionName', 'N/A')}\n"
            result += f"📅 Shoot Day: {call_sheet.get('shootDay', 'N/A')}\n"
            result += f"📍 Location: {call_sheet.get('location', 'N/A')}\n\n"
            
            if 'scenes' in call_sheet:
                result += "🎥 Scenes:\n"
                for scene in call_sheet['scenes'][:5]:  # First 5 scenes
                    result += f"  • Scene {scene.get('number')}: {scene.get('description')}\n"
            
            if 'crew' in call_sheet:
                result += f"\n👥 Crew call: {call_sheet['crew'].get('callTime', 'TBD')}\n"
            
            return result
        except Exception as e:
            return f"Error fetching call sheet: {str(e)}"
    
    async def get_my_tasks(self, filter_type: str = 'all') -> str:
        """Get user's tasks from Spring Boot API"""
        try:
            tasks = await self.api_client.get_tasks(self.user_id, filter_type)
            
            if not tasks:
                return f"No {filter_type} tasks found"
            
            result = f"✅ Tasks ({filter_type}):\n\n"
            for task in tasks[:10]:  # Show first 10
                status_icon = "✓" if task.get('completed') else "○"
                priority = task.get('priority', 'normal')
                priority_icon = "🔴" if priority == 'high' else "🟡" if priority == 'medium' else "⚪"
                
                result += f"{status_icon} {priority_icon} {task.get('title', 'Untitled')}\n"
                if task.get('dueDate'):
                    result += f"   Due: {task['dueDate']}\n"
                result += f"   ID: {task.get('id')}\n\n"
            
            return result
        except Exception as e:
            return f"Error fetching tasks: {str(e)}"
    
    async def complete_task(self, task_id: str) -> str:
        """Mark task as complete"""
        try:
            success = await self.api_client.complete_task(task_id, self.user_id)
            if success:
                return f"✅ Task {task_id} marked as complete!"
            else:
                return f"❌ Failed to complete task {task_id}"
        except Exception as e:
            return f"Error completing task: {str(e)}"
    
    async def get_timesheet_status(self) -> str:
        """Get timesheet status from Spring Boot API"""
        try:
            timesheet = await self.api_client.get_timesheet_status(self.user_id)
            
            status = timesheet.get('status', 'unknown')
            hours = timesheet.get('hoursWorked', 0)
            submitted = timesheet.get('submitted', False)
            
            result = f"⏱️ Timesheet Status:\n\n"
            result += f"Status: {'✅ Submitted' if submitted else '⚠️ Pending'}\n"
            result += f"Hours this week: {hours}\n"
            
            if not submitted:
                result += "\n💡 Remember to submit your timesheet by Friday!"
            
            return result
        except Exception as e:
            return f"Error fetching timesheet: {str(e)}"
    
    async def search_crew(self, query: str) -> str:
        """Search for crew member"""
        try:
            results = await self.api_client.search_crew(self.production_id, query)
            
            if not results:
                return f"No crew members found matching '{query}'"
            
            result = f"Search results for '{query}':\n\n"
            for person in results[:5]:  # Show first 5
                name = person.get('name', 'Unknown')
                role = person.get('role', 'N/A')
                dept = person.get('department', 'N/A')
                phone = person.get('phone', 'N/A')
                email = person.get('email', 'N/A')
                
                result += f"• {name} - {role}\n"
                result += f"  Dept: {dept}\n"
                result += f"  Phone: {phone}\n"
                result += f"  Email: {email}\n\n"
            
            return result
        except Exception as e:
            return f"Error searching crew: {str(e)}"
    
    async def get_production_status(self) -> str:
        """Get production status from Spring Boot API"""
        try:
            status = await self.api_client.get_production_status(self.production_id)
            
            if not status:
                return "Production status unavailable"
            
            result = f"Production Status:\n\n"
            result += f"Name: {status.get('name', 'N/A')}\n"
            result += f"Status: {status.get('status', 'N/A')}\n"
            result += f"Shoot Days: {status.get('currentDay', 0)}/{status.get('totalDays', 0)}\n"
            result += f"Budget: {status.get('budgetSpent', 0)}% spent\n"
            
            if 'nextMilestone' in status:
                result += f"\nNext milestone: {status['nextMilestone']}\n"
            
            return result
        except Exception as e:
            return f"Error fetching production status: {str(e)}"
    
    async def get_notifications(self) -> str:
        """Get unread notifications"""
        try:
            notifications = await self.api_client.get_notifications(
                self.user_id, 
                unread_only=True
            )
            
            if not notifications:
                return "No new notifications"
            
            result = f"Notifications ({len(notifications)} unread):\n\n"
            for notif in notifications[:5]:  # Show first 5
                type_icon = {
                    'schedule': '📅',
                    'task': '✅',
                    'message': '💬',
                    'alert': '⚠️'
                }.get(notif.get('type'), '📢')
                
                result += f"{type_icon} {notif.get('message', 'No message')}\n"
                if notif.get('timestamp'):
                    result += f"   {notif['timestamp']}\n"
                result += "\n"
            
            return result
        except Exception as e:
            return f"Error fetching notifications: {str(e)}"
    
    # ==================== MAIN CHAT INTERFACE ====================
    
    async def chat(self, message: str) -> Dict:
        """Main chat interface with Spring Boot backend"""
        
        if not self.agent:
            return {
                "response": "Assistant not initialized. Call initialize() first.",
                "suggestions": []
            }
        
        output = None
        
        try:
            # Get current context from API
            context = await self._get_current_context()
            
            # Add context to message
            context_str = json.dumps(context, indent=2)
            enhanced_message = f"{message}\n\n[System Context: {context_str}]"
            
            # Try agent first
            response = await self.agent.ainvoke({
                "input": enhanced_message
            })
            
            output = response.get('output', None)
            
            # Clean up output
            if output and isinstance(output, str):
                if output.startswith("Final Answer:"):
                    output = output.replace("Final Answer:", "").strip()
                if "Action: None" in output:
                    output = output.split("Action: None")[0].strip()
            
            # Fallback if agent failed
            if not output or output == "Agent stopped due to iteration limit or time limit.":
                raise Exception("Agent failed to generate response")
                
        except Exception as e:
            print(f"Agent error: {e}, using direct LLM fallback")
            
            # Fallback: Direct LLM call
            fallback_prompt = f"""You are {self.user_profile.get('name', 'User')}'s personal assistant.

User role: {self.user_profile.get('role', 'N/A')}
Current time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}

User says: {message}

Respond naturally and helpfully. Be concise and friendly."""
            
            output = await self.llm._acall(fallback_prompt)
        
        return {
            "response": output,
            "suggestions": await self._generate_smart_suggestions(),
            "provider": self.llm_provider
        }
    
    async def _get_current_context(self) -> Dict:
        """Build current context from API data"""
        context = {
            'timestamp': datetime.now().isoformat(),
            'day_of_week': datetime.now().strftime('%A'),
            'time_of_day': 'morning' if datetime.now().hour < 12 else 'afternoon' if datetime.now().hour < 17 else 'evening'
        }
        
        try:
            # Add next call time if available
            next_call = await self.api_client.get_next_call_time(
                self.user_id, 
                self.production_id
            )
            if next_call:
                context['next_call_time'] = next_call.get('callTime')
        except:
            pass
        
        try:
            # Add unread notifications count
            notifications = await self.api_client.get_notifications(
                self.user_id, 
                unread_only=True
            )
            context['unread_notifications'] = len(notifications)
        except:
            pass
        
        return context
    
    async def _generate_smart_suggestions(self) -> List[str]:
        """Generate contextual suggestions"""
        suggestions = []
        
        try:
            # Check for pending tasks
            tasks = await self.api_client.get_tasks(self.user_id, 'today')
            if tasks:
                suggestions.append("Show me today's tasks")
        except:
            pass
        
        try:
            # Check for next call time
            next_call = await self.api_client.get_next_call_time(
                self.user_id, 
                self.production_id
            )
            if next_call:
                suggestions.append("When is my next call time?")
        except:
            pass
        
        suggestions.extend([
            "What's on my schedule today?",
            "Show me the call sheet"
        ])
        
        return suggestions[:4]  # Max 4 suggestions
    
    async def proactive_check(self) -> List[Dict]:
        """Background monitoring for proactive alerts"""
        
        if not self.proactive_enabled:
            return []
        
        alerts = []
        
        try:
            # Check for upcoming call time
            next_call = await self.api_client.get_next_call_time(
                self.user_id, 
                self.production_id
            )
            
            if next_call:
                call_time = datetime.fromisoformat(next_call['callTime'])
                hours_until = (call_time - datetime.now()).total_seconds() / 3600
                
                # Alert 12 hours before
                if 11.5 < hours_until < 12.5:
                    alerts.append({
                        'type': 'call_time_reminder',
                        'priority': 'medium',
                        'message': f"You have a {call_time.strftime('%-I:%M %p')} call tomorrow at {next_call.get('location', 'TBD')}",
                        'actions': ['view_call_sheet', 'dismiss']
                    })
                
                # Alert 1 hour before
                elif 0.5 < hours_until < 1.5:
                    alerts.append({
                        'type': 'call_time_imminent',
                        'priority': 'high',
                        'message': f"Call time in 1 hour! {call_time.strftime('%-I:%M %p')} at {next_call.get('location', 'TBD')}",
                        'actions': ['view_call_sheet', 'snooze']
                    })
        except Exception as e:
            print(f"Error in proactive check: {e}")
        
        try:
            # Check for overdue tasks
            tasks = await self.api_client.get_tasks(self.user_id, 'overdue')
            if len(tasks) > 0:
                alerts.append({
                    'type': 'overdue_tasks',
                    'priority': 'medium',
                    'message': f"You have {len(tasks)} overdue task(s)",
                    'actions': ['view_tasks', 'dismiss']
                })
        except Exception as e:
            print(f"Error checking tasks: {e}")
        
        try:
            # Check timesheet submission
            timesheet = await self.api_client.get_timesheet_status(self.user_id)
            if not timesheet.get('submitted') and datetime.now().weekday() >= 4:  # Thursday or Friday
                alerts.append({
                    'type': 'timesheet_reminder',
                    'priority': 'medium',
                    'message': "Don't forget to submit your timesheet for this week!",
                    'actions': ['view_timesheet', 'dismiss']
                })
        except Exception as e:
            print(f"Error checking timesheet: {e}")
        
        return alerts
    
    async def cleanup(self):
        """Cleanup resources"""
        await APIClientManager.close_client(self.user_id)


# ==================== FACTORY & SESSION MANAGEMENT ====================

class AssistantFactory:
    """
    Factory for creating and managing personal assistants
    Integrates with user authentication system
    """
    
    _assistants: Dict[str, PersonalAssistant] = {}
    
    @classmethod
    async def create_assistant(
        cls, 
        user_id: str, 
        auth_token: str, 
        production_id: str = None
    ) -> PersonalAssistant:
        """
        Create and initialize a personal assistant for user
        Call this after successful login
        """
        
        # Check if assistant already exists
        if user_id in cls._assistants:
            return cls._assistants[user_id]
        
        # Create new assistant
        assistant = PersonalAssistant(
            user_id=user_id,
            auth_token=auth_token,
            production_id=production_id,
            llm_provider="groq"  # Can be "groq" or "gemini"
        )
        
        # Initialize (loads user profile from Spring Boot)
        await assistant.initialize()
        
        # Store in cache
        cls._assistants[user_id] = assistant
        
        return assistant
    
    @classmethod
    def get_assistant(cls, user_id: str) -> Optional[PersonalAssistant]:
        """Get existing assistant"""
        return cls._assistants.get(user_id)
    
    @classmethod
    async def remove_assistant(cls, user_id: str):
        """Remove assistant (call on logout)"""
        if user_id in cls._assistants:
            await cls._assistants[user_id].cleanup()
            del cls._assistants[user_id]
    
    @classmethod
    async def cleanup_all(cls):
        """Cleanup all assistants"""
        for assistant in cls._assistants.values():
            await assistant.cleanup()
        cls._assistants.clear()
        await APIClientManager.close_all()