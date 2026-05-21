import json
from app.graphs.placement_graph import placement_graph

print("Input Schema:")
print(json.dumps(placement_graph.input_schema.schema(), indent=2))

print("\nOutput Schema:")
print(json.dumps(placement_graph.output_schema.schema(), indent=2))

print("\nConfig Schema:")
print(json.dumps(placement_graph.config_schema.schema(), indent=2))
