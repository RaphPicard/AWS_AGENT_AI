#In this lab, we will create a Strands agent to check on the inventory of the products. 
# The customer will be able to ask the agent for available clothes in the catalogue.


# import all libraries
import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import use_aws

region = boto3.Session().region_name


model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0", # update with the model you want to use
    region_name=region,
    temperature=0.3,
    #top_p=0.8
)

aws_agent = Agent(tools=[use_aws])  # use_aws : For fetching data from DynamoDB, S3...
#This tool enables the agent to interact with AWS services through their APIs.
#It supports operations across all AWS services including DynamoDB, S3, Lambda, and CloudWatch, handles authentication and credential management automatically, and returns structured responses from AWS operations.



@tool
def get_product(product_id: str):
    """
    Use this tool when you need to get the details of a product to 
    see if that's available in stock or not.

    Args:
        product_id: The id of the product

    """
    print(f"Getting product from Dynamodb with the input {product_id}")

    get_item_result = aws_agent.tool.use_aws(
        service_name="dynamodb",
        operation_name="get_item",
        parameters={
            "TableName": "anycompany_product_inventory",
            "Key":{
                "product_id": {
                    "S": product_id
            }
            }
            },
        region=region,
        label="Get One Item"
    )
    return get_item_result


_system_prompt = """
You are an Agent that checks if a product is available in the inventory.
Return output in the below JSON format. Do not include any other text.
{
    "product_id" : PRODUCT_ID,
    "in_stock": IN_STOCK_VALUE
}

where IN_STOCK_VALUE = "yes" if quantity_available is > 0 and "no" otherwise.
"""

# Register the tool with the agent
inventory_agent = Agent(
    model=model,
    tools=[get_product],
    system_prompt=_system_prompt
)

product_agent_response = inventory_agent("What is the available quantity for PROD-048?")
print(product_agent_response)

quantity_agent_response = inventory_agent("How many PROD-028 are available?")
print(quantity_agent_response)

product_agent_response = inventory_agent("Show me the first product you find?")
print(product_agent_response)