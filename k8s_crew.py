import subprocess
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

# Connect from inside Docker to Ollama running on your host machine
local_llm = LLM(
    model="ollama/qwen2.5-coder:7b",
    base_url="http://docker.internal"
)

# Tool 1: SecOps Checkov Scanner
@tool("Scan Kubernetes YAML")
def scan_k8s_yaml(yaml_content: str) -> str:
    """Writes manifest to deployment.yaml and audits it with Checkov."""
    with open("deployment.yaml", "w") as f:
        f.write(yaml_content)
    
    res = subprocess.run(
        ["checkov", "-f", "deployment.yaml", "--framework", "kubernetes", "--compact", "--quiet"],
        capture_output=True, text=True
    )
    return res.stdout if res.stdout else "Checkov scan passed with zero issues."

# Tool 2: Live Cluster Deployer & Debugger
@tool("Deploy and Check Pods")
def deploy_and_inspect(yaml_content: str) -> str:
    """Applies deployment.yaml to Kind cluster and returns pod status and events."""
    with open("deployment.yaml", "w") as f:
        f.write(yaml_content)
        
    apply_res = subprocess.run(["kubectl", "apply", "-f", "deployment.yaml"], capture_output=True, text=True)
    if apply_res.returncode != 0:
        return f"Apply failed:\n{apply_res.stderr}"
    
    status_res = subprocess.run(["kubectl", "get", "pods", "-o", "wide"], capture_output=True, text=True)
    events_res = subprocess.run(["kubectl", "get", "events", "--sort-by=.lastTimestamp"], capture_output=True, text=True)
    return f"APPLY OUTPUT:\n{apply_res.stdout}\n\nPODS:\n{status_res.stdout}\n\nRECENT EVENTS:\n{events_res.stdout[-1000:]}"

# Agent 1: Platform Architect
architect = Agent(
    role="Kubernetes Platform Engineer",
    goal="Generate clean, valid Kubernetes Deployment YAML manifests.",
    backstory="You design resilient containerized workloads for Kubernetes.",
    llm=local_llm,
    verbose=True
)

# Agent 2: DevSecOps Gatekeeper
secops = Agent(
    role="Kubernetes Security Auditor",
    goal="Audit Kubernetes manifests with Checkov and enforce security contexts, resource limits, and non-root users.",
    backstory="You block privileged containers and missing resource limits before deployment.",
    tools=[scan_k8s_yaml],
    llm=local_llm,
    verbose=True
)

# Agent 3: Site Reliability Engineer (SRE)
sre = Agent(
    role="Site Reliability Engineer",
    goal="Deploy verified YAML to the live Kind cluster, verify pods reach Running state, and fix runtime errors.",
    backstory="You deploy manifests to Kubernetes and troubleshoot CrashLoopBackOff or ImagePullBackOff issues.",
    tools=[deploy_and_inspect],
    llm=local_llm,
    verbose=True
)

# Tasks
build_task = Task(
    description="Write a Kubernetes Deployment YAML for an 'nginx:alpine' web server named 'secure-web' with 2 replicas. Output raw YAML only.",
    expected_output="Valid Kubernetes Deployment YAML.",
    agent=architect
)

audit_task = Task(
    description=(
        "Scan the Architect's YAML using the Checkov tool. Fix high-severity security issues "
        "(such as missing CPU/memory limits or runAsNonRoot) and output the hardened YAML."
    ),
    expected_output="Hardened Kubernetes Deployment YAML.",
    agent=secops
)

deploy_task = Task(
    description=(
        "Take the hardened YAML from SecOps and deploy it to the Kind cluster using the Deploy and Check Pods tool. "
        "Inspect the pods and events. If any pod fails to start due to strict security settings (like nginx failing as non-root on port 80), "
        "adjust the YAML (e.g., use unprivileged port 8080 or writable /tmp volume) and redeploy until healthy."
    ),
    expected_output="Confirmation that pods are deployed and a summary of runtime fixes made.",
    agent=sre
)

crew = Crew(
    agents=[architect, secops, sre],
    tasks=[build_task, audit_task, deploy_task],
    verbose=True
)

print(crew.kickoff())
