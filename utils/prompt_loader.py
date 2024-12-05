import os
import json
def load_prompt_template(template_name: str) -> str:
    """Load a prompt template from the templates directory."""
    template_path = os.path.join('templates', template_name)
    with open(template_path, 'r') as f:
        return f.read()

def format_conversation_prompt(template: str, text: str, current_graph: dict, all_paths: dict) -> str:
    """Format the conversation analysis prompt with current data."""
    try:
        # Ensure we're passing strings for JSON data
        graph_keys = json.dumps(list(current_graph.keys())).replace('"', "'")
        paths = json.dumps(all_paths).replace('"', "'")
        
        formatted = template.format(
            text=text,
            current_graph_keys=graph_keys,
            all_paths=paths,
            pastPaths=paths
        )
        return formatted
    except Exception as e:
        print(f"Error formatting prompt: {str(e)}")
        return None