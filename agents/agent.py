import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment


class BaseAgent:
    """Base agent class. All specialized agents inherit from this."""

    name = "Base Agent"
    system_prompt = "You are a helpful AI assistant."

    def run(self, task: str) -> str:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=self.system_prompt,
            messages=[{"role": "user", "content": task}],
        )
        return next(
            (block.text for block in response.content if block.type == "text"), ""
        )


class MarketingAgent(BaseAgent):
    name = "Marketing Agent"
    system_prompt = """You are an expert marketing AI agent. You specialize in:
- Creating marketing campaigns and strategies
- Writing compelling copy and content
- Analyzing market trends and audience targeting
- Suggesting growth and engagement strategies

Be specific, actionable, and data-driven in your recommendations."""


class SalesAgent(BaseAgent):
    name = "Sales Agent"
    system_prompt = """You are an expert sales AI agent. You specialize in:
- Crafting sales pitches and outreach messages
- Objection handling strategies
- Lead qualification and pipeline management
- Closing techniques and follow-up sequences

Be persuasive, concise, and focused on customer value."""


class CustomerSupportAgent(BaseAgent):
    name = "Customer Support Agent"
    system_prompt = """You are an expert customer support AI agent. You specialize in:
- Resolving customer complaints and issues
- Writing empathetic and helpful responses
- Drafting FAQ content and help documentation
- Escalation decision-making

Always be empathetic, clear, and solution-focused."""


class OperationsAgent(BaseAgent):
    name = "Operations Agent"
    system_prompt = """You are an expert operations AI agent. You specialize in:
- Optimizing internal workflows and processes
- Writing SOPs and documentation
- Identifying bottlenecks and inefficiencies
- Resource planning and scheduling

Be systematic, precise, and efficiency-focused."""


class OrchestratorAgent(BaseAgent):
    """Routes tasks to the right department agent."""

    name = "Orchestrator"
    system_prompt = """You are an orchestrator AI. Given a task, decide which department should handle it.
Reply with ONLY one of these words: marketing, sales, support, operations.
- marketing: campaigns, content, branding, audience, growth
- sales: pitches, leads, deals, outreach, revenue
- support: customer issues, complaints, help, refunds, FAQs
- operations: workflows, processes, internal tasks, scheduling, documentation"""

    AGENTS = {
        "marketing": MarketingAgent(),
        "sales": SalesAgent(),
        "support": CustomerSupportAgent(),
        "operations": OperationsAgent(),
    }

    def run(self, task: str) -> dict:
        """Route task to appropriate agent and return result with metadata."""
        routing_response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=10,
            system=self.system_prompt,
            messages=[{"role": "user", "content": task}],
        )
        department = next(
            (block.text.strip().lower() for block in routing_response.content if block.type == "text"),
            "operations"
        )

        # Fall back to operations if routing gives an unexpected value
        agent = self.AGENTS.get(department, self.AGENTS["operations"])
        result = agent.run(task)

        return {
            "department": department,
            "agent_name": agent.name,
            "result": result,
        }
