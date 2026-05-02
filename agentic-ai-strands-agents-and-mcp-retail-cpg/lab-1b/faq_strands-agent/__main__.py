"""Allow running this folder directly with: python3 lab-1b/faq_strands-agent"""

from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("faq_strands_agent.py")), run_name="__main__")
