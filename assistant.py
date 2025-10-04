# assistant/personal_assistant.py

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.llms.base import LLM
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime, timedelta
import os
import json
import redis
import chromadb
from groq import Groq
from pydantic import Field


class GroqLLM(LLM):
    """
    Custom LangChain wrapper for Groq API
    Blazing fast inference with Llama 3, Mixtral, Gemma
    """
    
    client: Any = Field(default=None, exclude=True)
    model: str = "llama-3.3-70b-versatile"  # Current available model
    temperature: float = 0.7
    max_tokens: int = 4096
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    @property
    def _llm_type(self) -> str:
        return "groq"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Synchronous call to Groq"""
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
        """Async call to Groq"""
        # Groq client doesn't have native async, so we'll use sync in executor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await asyncio.get_event_loop().run_in_executor(
                executor, self._call, prompt, stop
            )


class GeminiLLM(LLM):
    """
    Custom LangChain wrapper for Google Gemini API
    """
    
    client: Any = Field(default=None, exclude=True)
    model: str = "gemini-1.5-flash"
    temperature: float = 0.7
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.client = genai.GenerativeModel(self.model)
    
    @property
    def _llm_type(self) -> str:
        return "gemini"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Synchronous call to Gemini"""
        try:
            response = self.client.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error calling Gemini: {str(e)}"
    
    async def _acall(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Async call to Gemini"""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await asyncio.get_event_loop().run_in_executor(
                executor, self._call, prompt, stop
            )


class PersonalAssistant:
    """
    Personal AI Assistant for each user
    Context-aware, proactive, helpful
    Now powered by Groq (blazing fast!) or Google Gemini
    """
    
    def __init__(
        self,
        user_id: str,
        user_profile: Dict,
        production_id: str = None,
        llm_provider: str = "groq"  # "groq" or "gemini"
    ):
        self.user_id = user_id
        self.user_profile = user_profile
        self.production_id = production_id
        self.llm_provider = llm_provider
        
        # Initialize LLM based on provider
        self.llm = self._initialize_llm(llm_provider)
        
        # Memory systems
        self.conversation_memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10  # Remember last 10 messages
        )
        
        self.long_term_memory = UserMemory(user_id)
        self.context_engine = ContextEngine(user_id, production_id)
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create agent
        self.agent = self._create_agent()
        
        # Proactive monitoring
        self.proactive_enabled = True
    
    def _initialize_llm(self, provider: str):
        """
        Initialize LLM based on provider choice
        """
        if provider == "groq":
            # Groq - SUPER FAST inference with open models
            # Current available models (as of Oct 2024):
            # - llama-3.3-70b-versatile (best quality, latest)
            # - llama-3.1-8b-instant (fastest)
            # - mixtral-8x7b-32768 (great for reasoning, 32k context)
            # - gemma2-9b-it (fast, good quality)
            
            return GroqLLM(
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=4096
            )
        
        elif provider == "gemini":
            # Google Gemini - Great reasoning, multimodal
            # Available models:
            # - gemini-1.5-flash (fastest, cost-effective)
            # - gemini-1.5-pro (best quality, multimodal)
            
            return GeminiLLM(
                model="gemini-1.5-flash",
                temperature=0.7
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Use 'groq' or 'gemini'")
    
    def _create_agent(self) -> AgentExecutor:
        """
        Create personalized agent with role-specific prompt
        Using ReAct pattern for better tool usage
        """
        
        # Get role-specific system prompt
        system_prompt = self._get_role_prompt()
        
        # Simplified prompt that works better with Groq models
        template = """{system_prompt}

You have access to the following tools:

{tools}

To use a tool, use this EXACT format:
Action: tool_name
Action Input: the input

If you can answer without a tool, respond directly with your answer (do NOT write "Action: None" or "Final Answer:").

Previous conversation:
{chat_history}

User: {input}
{agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "chat_history", "agent_scratchpad"],
            partial_variables={
                "system_prompt": system_prompt,
                "tools": self._format_tools(),
                "tool_names": ", ".join([t.name for t in self.tools])
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
            handle_parsing_errors="Check your output and make sure it conforms! Use 'Action:' and 'Action Input:' or respond directly.",
            max_iterations=3,  # Reduced from 5 to fail faster
            early_stopping_method="generate",  # Generate a response even if max iterations reached
            return_intermediate_steps=False
        )
    
    def _format_tools(self) -> str:
        """Format tools for prompt"""
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
    
    def _get_role_prompt(self) -> str:
        """
        Generate role-specific system prompt
        """
        
        base_prompt = f"""You are a personal AI assistant for {self.user_profile['name']}, 
a {self.user_profile['role']} working on the production "{self.user_profile.get('production_name', 'current production')}".

Your personality:
- Friendly, professional, and efficient
- Proactive - anticipate needs before asked
- Conversational but respectful
- Use casual language appropriate for film crew
- Call the user by their preferred name: {self.user_profile.get('preferred_name', self.user_profile['name'])}

Your responsibilities:
1. Help manage their schedule and tasks
2. Answer questions about the production
3. Remind them of important deadlines and call times
4. Assist with routine administrative tasks
5. Provide relevant information based on their role
6. Learn their preferences and adapt

Current context:
- User role: {self.user_profile['role']}
- Department: {self.user_profile.get('department', 'N/A')}
- Current time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}
- Production status: {self.user_profile.get('production_status', 'Active')}

Communication style:
- Be concise but thorough
- Use emojis occasionally to be friendly (but not excessive)
- When giving schedules, format clearly
- Always confirm before taking actions that affect others
- If unsure, ask clarifying questions

Remember:
- You have access to their personal schedule, tasks, and production information
- Always prioritize their time and focus
- Suggest proactive solutions, not just answer questions
- Respect their privacy and only access information they're authorized to see
"""

        # Add role-specific guidance
        role_prompts = {
            'Producer': """
Additional context for Producer role:
- Focus on high-level production status
- Provide budget insights and forecasts
- Alert to critical issues requiring decisions
- Help prioritize competing demands
- Summarize reports and data
""",
            'Production Manager': """
Additional context for PM role:
- Help coordinate between departments
- Track logistics and resources
- Manage daily operations
- Alert to schedule conflicts
- Assist with crew coordination
""",
            'Assistant Director': """
Additional context for AD role:
- Focus on schedule and call sheets
- Help track shooting progress
- Coordinate with talent and crew
- Monitor daily progress vs plan
- Assist with on-set logistics
""",
            'Department Head': """
Additional context for Department Head:
- Focus on their department's needs
- Track department budget and resources
- Help manage department crew
- Coordinate with other departments
- Monitor equipment and supplies
""",
            'Crew': """
Additional context for Crew member:
- Keep information simple and relevant
- Focus on their personal schedule
- Help with timesheets and expenses
- Provide necessary daily information
- Answer questions about production
"""
        }
        
        role = self.user_profile['role']
        role_specific = role_prompts.get(role, role_prompts['Crew'])
        
        return base_prompt + role_specific
    
    def _initialize_tools(self) -> List:
        """
        Initialize tools the assistant can use
        """
        from langchain.tools import Tool
        
        return [
            Tool(
                name="get_my_schedule",
                func=self.get_my_schedule,
                description="Get user's personal schedule. Input: date (YYYY-MM-DD), 'today', 'tomorrow', 'this_week'"
            ),
            Tool(
                name="get_next_call_time",
                func=self.get_next_call_time,
                description="Get user's next call time. No input needed."
            ),
            
            Tool(
                name="get_my_tasks",
                func=self.get_my_tasks,
                description="Get user's tasks. Input: 'all', 'today', 'overdue', or 'completed'"
            ),
            Tool(
                name="complete_task",
                func=self.complete_task,
                description="Mark a task as complete. Input: task_id"
            ),
            
            # Timesheets
            Tool(
                name="get_timesheet_status",
                func=self.get_timesheet_status,
                description="Get user's timesheet status for current week. No input needed."
            ),
            
            # Production Info
            Tool(
                name="get_call_sheet",
                func=self.get_call_sheet,
                description="Get call sheet. Input: date (YYYY-MM-DD) or 'today' or 'tomorrow'"
            ),
            Tool(
                name="search_crew",
                func=self.search_crew,
                description="Find crew member contact info. Input: name or role"
            ),
            
            # Preferences
            Tool(
                name="set_preference",
                func=self.set_preference,
                description="Save a user preference. Input: 'key:value' format"
            ),
        ]
    
    async def chat(self, message: str) -> Dict:
        """
        Main chat interface with robust fallback
        """
        
        # Get current context
        context = await self.context_engine.get_current_context()
        
        # Add context to message
        context_str = json.dumps(context, indent=2)
        enhanced_message = f"{message}\n\n[System Context: {context_str}]"
        
        output = None
        
        try:
            # Try agent first
            response = await self.agent.ainvoke({
                "input": enhanced_message
            })
            
            output = response.get('output', None)
            
            # Clean up the output - remove "Final Answer:" prefix if present
            if output and isinstance(output, str):
                if output.startswith("Final Answer:"):
                    output = output.replace("Final Answer:", "").strip()
                # Remove "Action: None" artifacts
                if "Action: None" in output:
                    output = output.split("Action: None")[0].strip()
            
            # If agent failed or returned empty, use fallback
            if not output or output == "Agent stopped due to iteration limit or time limit.":
                raise Exception("Agent failed to generate response")
                
        except Exception as e:
            print(f"Agent error: {e}, using direct LLM fallback")
            
            # Fallback: Use direct LLM call with simpler prompt
            fallback_prompt = f"""You are {self.user_profile['preferred_name']}'s personal assistant.

User role: {self.user_profile['role']}
Current time: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}

User says: {message}

Respond naturally and helpfully as their assistant. Be concise and friendly."""
            
            output = await self.llm._acall(fallback_prompt)
        
        # Store interaction in long-term memory (non-blocking)
        try:
            await self.long_term_memory.store_interaction(
                query=message,
                response=output,
                context=context
            )
        except Exception as e:
            print(f"Memory storage failed: {e}")
        
        return {
            "response": output,
            "suggestions": await self.generate_smart_suggestions(context),
            "provider": self.llm_provider
        }
    
    async def proactive_check(self):
        """
        Background monitoring - runs every few minutes
        Proactively suggests helpful actions
        """
        
        if not self.proactive_enabled:
            return []
        
        context = await self.context_engine.get_current_context()
        suggestions = []
        
        # Check upcoming call time
        try:
            next_call = await self.get_next_call_time()
            if next_call and isinstance(next_call, dict):
                call_time = datetime.fromisoformat(next_call['call_time'])
                hours_until = (call_time - datetime.now()).total_seconds() / 3600
                
                # Alert 12 hours before
                if 11.5 < hours_until < 12.5:
                    suggestions.append({
                        'type': 'call_time_reminder',
                        'priority': 'medium',
                        'message': f"👋 Hey! You have a {call_time.strftime('%-I:%M %p')} call tomorrow.",
                        'actions': ['view_call_sheet', 'dismiss']
                    })
        except Exception as e:
            print(f"Error checking call time: {e}")
        
        return suggestions
    
    # Tool Implementation Methods (Placeholders - connect to your API)
    
    def get_my_schedule(self, date_input: str) -> str:
        """Get user's schedule"""
        return f"Schedule for {date_input}: [Mock data - connect to your API]"
    
    def get_next_call_time(self) -> Optional[Dict]:
        """Get user's next call time"""
        # Mock response
        tomorrow = datetime.now() + timedelta(days=1)
        return {
            "call_time": tomorrow.replace(hour=7, minute=0).isoformat(),
            "location": "Studio Lot B",
            "location_type": "INT"
        }
    
    def get_my_tasks(self, filter: str = 'all') -> str:
        """Get user's tasks"""
        return f"Tasks ({filter}): [Mock data - connect to your API]"
    
    def complete_task(self, task_id: str) -> str:
        """Mark task as complete"""
        return f"Task {task_id} marked complete"
    
    def get_timesheet_status(self) -> Dict:
        """Get timesheet status"""
        return {"status": "pending", "hours": 40}
    
    def get_call_sheet(self, date: str) -> str:
        """Get call sheet"""
        return f"Call sheet for {date}: [Mock data]"
    
    def search_crew(self, query: str) -> str:
        """Search for crew member"""
        return f"Crew search results for '{query}': [Mock data]"
    
    def set_preference(self, key_value: str) -> str:
        """Save user preference"""
        try:
            key, value = key_value.split(":", 1)
            asyncio.create_task(self.long_term_memory.set_preference(key.strip(), value.strip()))
            return f"Preference '{key}' saved"
        except:
            return "Error: Use format 'key:value'"
    
    async def generate_smart_suggestions(self, context: Dict) -> List[str]:
        """Generate smart suggestions"""
        return []


class ContextEngine:
    """Builds rich context about user's current situation"""
    
    def __init__(self, user_id: str, production_id: str):
        self.user_id = user_id
        self.production_id = production_id
    
    async def get_current_context(self) -> Dict:
        """Gather all relevant context"""
        return {
            'timestamp': datetime.now().isoformat(),
            'day_of_week': datetime.now().strftime('%A'),
            'time_of_day': 'morning' if datetime.now().hour < 12 else 'afternoon' if datetime.now().hour < 17 else 'evening'
        }


class UserMemory:
    """Long-term memory for user preferences"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis not available: {e}")
            self.redis_client = None
        
        # Disable ChromaDB for now to avoid slow downloads
        # You can enable it later once the embedding model is downloaded
        self.vector_db = None
        self.collection = None
        
        # Uncomment below to enable ChromaDB (will download ~80MB embedding model on first run)
        # try:
        #     self.vector_db = chromadb.PersistentClient(path="./user_memory")
        #     self.collection = self.vector_db.get_or_create_collection(
        #         name=f"user_{user_id}_memory"
        #     )
        # except Exception as e:
        #     print(f"ChromaDB not available: {e}")
        #     self.collection = None
    
    async def store_interaction(self, query: str, response: str, context: Dict):
        """Store conversation"""
        if not self.collection:
            return
        try:
            self.collection.add(
                documents=[f"Q: {query}\nA: {response}"],
                metadatas=[{"timestamp": datetime.now().isoformat()}],
                ids=[f"int_{datetime.now().timestamp()}"]
            )
        except Exception as e:
            print(f"Store failed: {e}")
    
    async def get_preferences(self) -> Dict:
        """Get preferences"""
        return {}
    
    async def set_preference(self, key: str, value: Any):
        """Set preference"""
        if self.redis_client:
            try:
                self.redis_client.hset(f"user:{self.user_id}:prefs", key, json.dumps(value))
            except Exception as e:
                print(f"Pref save failed: {e}")