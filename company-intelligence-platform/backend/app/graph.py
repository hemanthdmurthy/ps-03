# app/graph.py
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.graphs.placement_graph import build_placement_graph

# Compile the observable Placement Graph without a custom checkpointer, 
# as required by LangGraph CLI and LangGraph Studio configuration.
graph = build_placement_graph(with_checkpointer=False)
