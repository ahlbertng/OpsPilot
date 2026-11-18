import subprocess
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

# Connect to your local Ollama instance
local_llm = LLM(
    model="ollama/qwen2.5-coder:7b",
    base_url="http://localhost:11434"
)

# Give the SecOps agent a real CLI tool
@tool("Run Checkov Security Scan")
def run_checkov(terraform_code: str) -> str:
    """Writes Terraform code to main.tf and scans it with Checkov."""
    with open("main.tf", "w") as f:
        f.write(terraform_code)
    
    result = subprocess.run(
        ["checkov", "-f", "main.tf", "--compact", "--quiet"],
        capture_output=True,
        text=True
    )
    return result.stdout if result.stdout else "Scan complete. No issues found."

# Define Agent 1: The Builder
architect = Agent(
    role="Senior AWS Cloud Architect",
    goal="Write clean, production-ready Terraform HCL code based on user specs.",
    backstory="You are an AWS specialist who builds scalable cloud infrastructure.",
    llm=local_llm,
    verbose=True
)

# Define Agent 2: The Gatekeeper
secops = Agent(
    role="Cloud Security Engineer",
    goal="Audit Terraform code using Checkov and ensure zero security vulnerabilities.",
    backstory="You block insecure deployments and enforce strict AWS compliance.",
    tools=[run_checkov],
    llm=local_llm,
    verbose=True
)

# Define the Workflow Tasks
write_tf_task = Task(
    description="Write Terraform code for an AWS S3 bucket named 'prod-app-logs-2026'. Output ONLY raw HCL code.",
    expected_output="Valid Terraform HCL code for an S3 bucket.",
    agent=architect
)

audit_tf_task = Task(
    description=(
        "Take the Terraform code from the Architect and scan it using the Checkov tool. "
        "If Checkov reports failed checks, rewrite the Terraform code to fix every issue, "
        "scan it again, and output the final secure HCL code."
    ),
    expected_output="A final, Checkov-verified Terraform file with a summary of fixes made.",
    agent=secops
)

# Run the Crew
crew = Crew(
    agents=[architect, secops],
    tasks=[write_tf_task, audit_tf_task],
    verbose=True
)

result = crew.kickoff()
print("\n=== FINAL VERIFIED INFRASTRUCTURE ===\n")
print(result)
