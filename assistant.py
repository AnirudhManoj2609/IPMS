from db_client import DatabaseClient
# You'll no longer need the 'auth_token' in the constructor

class PersonalAssistant:
    def __init__(
        self,
        user_id: str,
        # REMOVED: user_profile: Dict, (Will be fetched from DB)
        production_id: str = None,
        llm_provider: str = "groq"
    ):
        self.user_id = user_id
        self.production_id = production_id
        self.llm_provider = llm_provider
        self.user_profile = {} # Initialize empty, will be filled in initialize()

        # --- NEW DATABASE CLIENT INTEGRATION ---
        self.db_client = DatabaseClient()
        
        # Initialize LLM, Memory, Tools, and Agent (as before)
        self.llm = self._initialize_llm(llm_provider)
        self.conversation_memory = ConversationBufferWindowMemory(...) # as before
        self.long_term_memory = UserMemory(user_id) # as before
        self.context_engine = ContextEngine(user_id, production_id) # as before
        self.tools = self._initialize_tools() # as before
        self.agent = None # Initialize after profile is loaded
        self.proactive_enabled = True

    async def initialize(self):
        """
        Initializes DB connection, loads user profile, and creates the agent
        """
        await self.db_client.initialize_pool()
        
        # --- GET DATA FROM DB ---
        profile = await self.db_client.get_user_profile(self.user_id)
        if not profile:
            raise ValueError(f"User profile not found for ID: {self.user_id}")
            
        self.user_profile = profile
        self.production_id = self.user_profile.get('production_id', self.production_id)
        
        # --- CREATE AGENT (NOW WITH PROFILE DATA) ---
        self.agent = self._create_agent()
        
    async def cleanup(self):
        """Close DB connections"""
        await self.db_client.close()


    # =================================================================
    # TOOL IMPLEMENTATION METHODS (MOCK REPLACED WITH DB CALLS)
    # =================================================================
    
    async def get_my_schedule(self, date_input: str) -> str:
        """Get user's schedule from DB"""
        schedule = await self.db_client.get_schedule(self.user_id, date_input)
        if not schedule:
            return f"No scheduled events found for {date_input}."
        
        formatted_schedule = [
            f"- {item['event_name']} at {item['start_time'].strftime('%I:%M %p')} ({item['location']})"
            for item in schedule
        ]
        return f"Your schedule for {date_input}:\n" + "\n".join(formatted_schedule)
        
    async def get_next_call_time(self) -> str:
        """Get user's next call time from DB"""
        next_call = await self.db_client.get_next_call_time(self.user_id, self.production_id)
        if not next_call:
            return "No upcoming call time found for your current production."
        
        call_time = next_call['call_time'].strftime('%A, %B %d at %I:%M %p')
        return f"Your next call time is for '{next_call['event_name']}' on **{call_time}** at **{next_call['location']}**."

    async def get_my_tasks(self, filter: str = 'all') -> str:
        """Get user's tasks from DB"""
        tasks = await self.db_client.get_tasks(self.user_id, filter)
        if not tasks:
            return f"Great news! You have no {filter} tasks."
            
        formatted_tasks = [
            f"- ID: {item['task_id']}, Due: {item['due_date'].date()}, {item['description']}"
            for item in tasks
        ]
        return f"Your {filter} tasks:\n" + "\n".join(formatted_tasks)

    async def complete_task(self, task_id: str) -> str:
        """Mark task as complete in DB"""
        success = await self.db_client.complete_task(task_id, self.user_id)
        if success:
            return f"✅ Task **{task_id}** successfully marked as complete."
        return f"❌ Error: Could not find or complete task **{task_id}**."

    async def get_timesheet_status(self) -> str:
        """Get timesheet status from DB"""
        status = await self.db_client.get_timesheet_status(self.user_id)
        if status['status'] == 'submitted':
            return f"Your timesheet for this week is **submitted** with **{status['total_hours']}** hours recorded."
        return f"⚠️ Your timesheet is **{status['status']}**. Total hours logged so far: **{status['total_hours']}**."

    async def get_call_sheet(self, date_input: str) -> str:
        """Get call sheet from DB"""
        call_sheet = await self.db_client.get_call_sheet(self.production_id, date_input)
        if not call_sheet:
            return f"Call sheet not found for {date_input}."
        
        return f"Call Sheet for **{call_sheet['shoot_date']}**: Crew Call {call_sheet['crew_call']}, First Shot {call_sheet['first_shot']}, Location: {call_sheet['location_name']}."
        
    async def search_crew(self, query: str) -> str:
        """Search for crew member in DB"""
        results = await self.db_client.search_crew(self.production_id, query)
        if not results:
            return f"No crew members found matching '{query}' on this production."
            
        formatted_results = [
            f"- **{item['name']}** ({item['role']}) - Phone: {item['phone']}"
            for item in results
        ]
        return f"Found {len(results)} crew members:\n" + "\n".join(formatted_results)
        
    # NOTE: The set_preference method can still use Redis/Memory as before.
    # NOTE: The `proactive_check` and `generate_smart_suggestions` methods need updating to use `await self.get_next_call_time()`

    # Change the tool func assignments in _initialize_tools from lambda to the method
    def _initialize_tools(self) -> List:
        from langchain.tools import Tool
        
        # ... (list of tools) ...
        # Change `func=self.get_my_schedule` to `func=lambda date: asyncio.run(self.get_my_schedule(date))`
        # because LangChain tools expect sync functions or you need an async wrapper.
        # Since the `PersonalAssistant.chat` is async, we can use a small wrapper.
        
        return [
            Tool(
                name="get_my_schedule",
                func=lambda date: asyncio.run(self.get_my_schedule(date)),
                description="Get user's personal schedule. Input: date (YYYY-MM-DD), 'today', 'tomorrow', 'this_week'"
            ),
            # ... and so on for all your async tool methods ...
        ]