import os, time, docker
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

# Connect to the Ollama container over Docker's internal network
llm = LLM(model="ollama/qwen2.5-coder:3b", base_url="http://ollama:11434")
docker_client = docker.from_env()

@tool("Fetch Container Logs")
def get_container_logs(container_name: str) -> str:
    """Fetches the last 25 lines of logs from a running Docker container."""
    container = docker_client.containers.get(container_name)
    return container.logs(tail=25).decode("utf-8")

# Agent 1: Observability Specialist
detective = Agent(
    role="Log Detective",
    goal="Inspect container logs and extract exact error messages and patterns.",
    backstory="You monitor production microservices and filter out noise to find real failures.",
    tools=[get_container_logs],
    llm=llm,
    verbose=True
)

# Agent 2: Principal SRE
engineer = Agent(
    role="Principal SRE",
    goal="Diagnose the root cause of container errors and design concrete fixes.",
    backstory="You specialize in Python performance, database connection pooling, and Docker resource limits.",
    llm=llm,
    verbose=True
)

# Agent 3: Incident Commander
scribe = Agent(
    role="Incident Commander",
    goal="Produce a clean Markdown post-mortem and actionable remediation steps.",
    backstory="You write concise incident reports for engineering teams.",
    llm=llm,
    verbose=True
)

# Define Tasks
t1 = Task(
    description="Use the Fetch Container Logs tool to inspect the container named 'buggy-app'. Summarize every distinct error found.",
    expected_output="A bulleted list of raw errors and timestamps from buggy-app.",
    agent=detective
)

t2 = Task(
    description="Analyze the errors from the Log Detective. Explain why each failure happens and provide specific code or Docker Compose fixes.",
    expected_output="Root cause analysis with concrete Python and infrastructure fixes.",
    agent=engineer
)

t3 = Task(
    description="Combine the findings and fixes into a clean, professional Markdown Incident Report.",
    expected_output="A complete Markdown incident report with Executive Summary, Root Causes, and Remediation Checklist.",
    agent=scribe,
    output_file="/output/INCIDENT_REPORT.md"
)

# Wait briefly for buggy-app to generate logs and Ollama to load
time.sleep(10)

crew = Crew(agents=[detective, engineer, scribe], tasks=[t1, t2, t3], verbose=True)
crew.kickoff()
print("\n✅ Report saved to ./output/INCIDENT_REPORT.md")
