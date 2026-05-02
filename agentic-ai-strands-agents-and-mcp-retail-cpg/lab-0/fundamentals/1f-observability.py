import boto3
from strands import Agent
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
import json

region = boto3.Session().region_name

# Create a boto client config with custom settings
boto_config = BotocoreConfig(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=5,
    read_timeout=30
)

# Create a Bedrock model instance
bedrock_model = BedrockModel(
    model_id="us.amazon.nova-premier-v1:0", # try with different models you enabled access
    region_name=region,
    temperature=0.3,
    top_p=0.8,
    boto_client_config=boto_config,
)

agent = Agent()


tools_agent_response = agent("Tell me about agentic AI")

## print metrics summary
print("---------------------------------")
print(json.dumps(tools_agent_response.metrics.get_summary(), indent=4))
print("---------------------------------")
