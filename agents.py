from dataclasses import dataclass
import llm
from collections import defaultdict
import json
from llm import chat_with_gpt4
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
            TestAgent._dependency_graphs[self.agent_name] = {}
            

    def digest_text(self, text: str):
        """Digest text and learn more conversation paths."""
        currentGraph = TestAgent._dependency_graphs[self.agent_name]
        
        # Get all existing paths at the start
        allPaths = {}
        def build_paths_dict(graph, path=None):
            if path is None:
                path = []
            result = {}
            for q in graph:
                for r in graph[q]:
                    if q not in result:
                        result[q] = []
                    result[q].append(r)
                    nested = build_paths_dict(graph[q][r], path + [q, r])
                    result.update(nested)
            return result
        
        allPaths = build_paths_dict(currentGraph)
        
        # Track previous outputs
        previous_outputs = set()
        
        while True:
            # Build prompt with exact format provided
            currentPrompt = f'''[TASK]
"Your task is to analyze transcript segments from customer service interactions and identify both the current interaction type and the appropriate next step in the response pathway. Each segment includes the customer's request and the customer service representative's (CSR) reply. Utilizing the provided 'currentpath' and 'allpaths' data, determine the interaction type and then predict the next possible response categories from the paths available.

1. Review the dialogue snippet and understand the context of the interaction.
2. Consider the 'currentpath', which indicates the current state of the conversation. If you see a similar categorizaiton, report the same one in the currentGraph.
3. Examine 'allpaths', which lists all possible conversational paths and options.
4. Identify the type of interaction from 'currentpath'.
5. Determine the next response type by selecting an appropriate option from the linked list under the current interaction type in 'allpaths'.
6. Format your response as follows:
    - interaction_type: Type of the current interaction extracted from 'currentpath'.
    - response_type: The anticipated next step in the conversation from 'allpaths'.

Example analysis:
- Input text: 'Customer: I need help resetting my password. \nCSR: Can you verify your email associated with the account?'
  currentpath: 'PASSWORD_RESET', 
  allpaths: {{'PASSWORD_RESET': ['EMAIL_VERIFICATION', 'SECURITY_QUESTION'], 'EMAIL_VERIFICATION': ['SEND_RESET_LINK', 'VERIFY_IDENTITY']}}
- Output should be:
  interaction_type: PASSWORD_RESET
  response_type: EMAIL_VERIFICATION

Remember, your response impacts the effectiveness and fluency of a conversational model in real-world customer service scenarios. Accurate and intuitive interaction categorization is crucial for seamless automation and enhanced customer experience."
---

[FORMAT]
Follow the following format:

[INPUT]
text: text of the customer service call transcript
currentPath: {json.dumps(list(currentGraph.keys()), indent=2)}
allPaths: {json.dumps(allPaths, indent=2)}
[OUTPUT]
interaction_type: broad category of the question type in the conversation
response_type: broad category of the response type in the conversation

---

[EXAMPLES]

[Example 1]
[INPUT]
text: Customer: I need to cancel my service. 
CSR: Can you please provide your account number?
currentPath: 
allPaths: 
[OUTPUT]
interaction_type: CANCEL_SERVICE
response_type: ACCOUNT_NUMBER
---
[Example 2]
[INPUT]
text: Customer: Hi, I'm an existing customer. 
CSR: How can I assist you today?
currentPath: 
allPaths: 
[OUTPUT]
interaction_type: EXISTING_CUSTOMER
response_type: ACCOUNT_BALANCE
---
[Example 3]
[INPUT]
text: Customer: I'd like to speak to a supervisor. 
CSR: Let me go ahead and escalate that for you.
currentPath: 
allPaths: 
[OUTPUT]
interaction_type: ESCALATION_REQUEST
response_type: SUPERVISOR_ASSISTANCE
---
[Example 4]
[INPUT]
text: Customer: Hi, I'd like to open a new account. 
CSR: What type of account would you like to open?
currentPath: 
allPaths: 
[OUTPUT]
interaction_type: NEW_CUSTOMER
response_type: ACCOUNT_TYPE
---

For the given inputs, first generate your reasoning and then generate the outputs.

[INPUT]
text: {text}
nextSteps: {json.dumps(list(currentGraph.keys()), indent=2)}
allPaths: {json.dumps(allPaths, indent=2)}

[REASONING]
my_reasoning: <Your careful and step-by-step reasoning before you return the desired outputs for the given inputs>

[OUTPUT]
interaction_type: <Your output here that matches the format of interaction_type>
response_type: <Your output here that matches the format of response_type>'''
        
            # Get response from GPT
            response = chat_with_gpt4(currentPrompt)
            print(response)

            # Parse the response as a string
            try:
                # Assuming the response is formatted as:
                # "interaction_type: <type>\nresponse_type: <type>"
                lines = response.splitlines()
                interaction_type = None
                response_type = None

                for line in lines:
                    if line.startswith("interaction_type:"):
                        interaction_type = line.split(":", 1)[1].strip()
                    elif line.startswith("response_type:"):
                        response_type = line.split(":", 1)[1].strip()

                if interaction_type is None or response_type is None:
                    raise ValueError("Could not parse interaction_type or response_type")

                output_key = (interaction_type, response_type)
            except Exception as e:
                print(f"Error parsing response: {e}")
                return  # or handle the error appropriately
            
            # Update the graph with new relations
            if interaction_type not in currentGraph:
                currentGraph[interaction_type] = {}
            if response_type not in currentGraph[interaction_type]:
                currentGraph[interaction_type][response_type] = {}
            # Check for duplicate output
            if output_key in previous_outputs:
                print("Duplicate output detected. Exiting.")
                break
            else:
                previous_outputs.add(output_key)
                # Set flag to indicate graph needs update
                self.graph_needs_update = True
                # Process the response as needed

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
            
        graph_representation = traverse_graph(currentGraph)
        graph_text = '\n'.join(graph_representation)
        
        print("\n=== CAPABILITIES DEBUG INFO ===")
        print(f"Agent Name received: '{self.agent_name}'")
        print(f"Current Graph State: {currentGraph}")
        
        prompt = (
            f"You are generating scenarios for customers calling about {self.agent_name} services. "
            f"Create 3 realistic first-person statements that a customer might say when calling.\n\n"
            f"Context: The business name '{self.agent_name}' indicates the type of service provided.\n"
            f"Create scenarios that would be specific and relevant to this type of business.\n\n"
            f"Guidelines:\n"
            f"- Create scenarios ONLY relevant to {self.agent_name}\n"
            f"- Include both urgent and routine service requests\n"
            f"- Use natural, conversational language\n"
            f"- Make scenarios specific to what this business would handle\n"
            f"- Focus on common issues customers would call about\n\n"
            f"Return exactly 3 scenarios specific to {self.agent_name}, one per line:\n"
        )

        print(f"\nPrompt being sent to LLM:\n{prompt}")
        
        # Get scenarios from LLM
        raw_answer = llm.chat_with_gpt4(prompt)
        print("\nRaw LLM Response:")
        print(raw_answer)
        scenarios = raw_answer.strip().split('\n')
        
        # Return only 3 scenarios
        return scenarios[:3]

    @classmethod
    def get_agent_capabilities(cls, agent_name: str):
        """Get all discovered capabilities for a specific agent type."""
        return cls._dependency_graphs.get(agent_name, {})

    @classmethod
    def get_all_agents(cls):
        """Get list of all agent types that have been tested."""
        return list(cls._dependency_graphs.keys())

