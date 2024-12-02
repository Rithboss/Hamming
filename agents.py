from dataclasses import dataclass
import llm
from collections import defaultdict
@dataclass
class TestAgent:
    """
    A class to manage and test different AI agents and their capabilities.
    Maintains a static dependency graph across all instances of the same agent type.
    """
    agent_name: str
    # Static dictionary to store dependency graphs for all agent types
    _dependency_graphs = defaultdict(dict)
    def __post_init__(self):
        # Initialize dependency graph for this agent type if it doesn't exist
        if self.agent_name not in TestAgent._dependency_graphs:
            TestAgent._dependency_graphs[self.agent_name] = {
                "capabilities": set(),
                "conversation_paths": set(),
            }

    def digest_text(self, text: str):
        """Digest text and learn more conversation paths."""
        currentGraph = TestAgent._dependency_graphs[self.agent_name]
        
        currentPath = ""
        while True:
            # Get existing paths
            currentOptions = []
            for q in currentGraph.keys():
                for r in currentGraph[q].keys():
                    currentOptions.append(f"{q} (question), {r} (response)")
            
            # Build prompt with context
            currentPrompt = (
                f"{text}\n"
                f"Current conversation path: {currentPath}\n"
                f"Existing paths: {currentOptions}\n"
                "Give me the next step in the conversation. Return as: question, response. If there are no more questions, just tell me none"
            )
            
            # Get AI response

            currentResponse = llm.chat_with_gpt4(currentPrompt)
            if currentResponse == "none":
                break
            question, response = currentResponse.split(", ")
            
            currentGraph[question][response] = {}
            currentGraph = currentGraph[question][response]
            currentPath = "Question: " + question + ", Response: " + response + "\n"

    def discover_capabilities(self):
        """Generate new test prompts based on current dependency graph to discover more capabilities."""
        currentGraph = TestAgent._dependency_graphs[self.agent_name]
        
        # Convert graph to readable format for LLM
        graph_representation = []
        def traverse_graph(graph, level=0):
            result = []
            for question, responses in graph.items():
                if isinstance(responses, dict):
                    result.append("  " * level + f"Q: {question}")
                    for response, next_level in responses.items():
                        result.append("  " * level + f"R: {response}")
                        result.extend(traverse_graph(next_level, level + 1))
            return result
            
        graph_representation = traverse_graph(currentGraph["conversation_paths"])
        
        prompt = f"""Given this AI voice agent's current known conversation paths:

{'\n'.join(graph_representation)}

Generate 10 different customer scenarios that might expose new capabilities or paths.
Each scenario should be a brief initial customer statement.
Focus on edge cases and scenarios we haven't covered yet.
Return only the scenarios, one per line.

Example format:
"Hi, I need emergency plumbing service, my basement is flooding, and this is my budget"
"I'm calling to reschedule my appointment from yesterday, and I need to know the cancellation policy"
"""

        # Get scenarios from LLM
        scenarios = llm.chat_with_gpt4(prompt).strip().split('\n')
        
        return scenarios

    @classmethod
    def get_agent_capabilities(cls, agent_name: str):
        """Get all discovered capabilities for a specific agent type."""
        return cls._dependency_graphs.get(agent_name, {}).get("capabilities", set())

    @classmethod
    def get_all_agents(cls):
        """Get list of all agent types that have been tested."""
        return list(cls._dependency_graphs.keys())

