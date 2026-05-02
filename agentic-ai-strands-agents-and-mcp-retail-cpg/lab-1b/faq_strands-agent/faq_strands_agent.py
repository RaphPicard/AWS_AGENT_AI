import os
import sys
import boto3
from strands import Agent
from strands_tools import retrieve
from strands.tools import tool
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError

region = boto3.Session().region_name or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

##################################
# Get FAQ Knowledge Base ID from SSM Parameter Store
try:
    ssm_client = boto3.client('ssm', region_name=region)    # SSM (AWS Console : Systems Manager ==> Application Tools ==> Parameter Store) is a service that allows you to store and manage configuration data and secrets. Here we are using it to store the FAQ Knowledge Base ID securely, instead of hardcoding it in the script.
    response = ssm_client.get_parameter(Name="faq_kb_id")      #Name = id du paramètre que tu as créé dans SSM Parameter Store pour stocker le FAQ Knowledge Base ID. Assure-toi que ce paramètre existe et contient la valeur correcte avant de lancer le script.
    kb_id = response['Parameter']['Value']                   #Value = On a créé une  (Amazon Bedrock Service :) Knowledge Base (basée sur les documents d'AnyCompany) dans Amazon Bedrock, et on a stocké l'ID de cette Knowledge Base dans un paramètre SSM nommé "faq_kb_id". Ici, on récupère cette valeur pour l'utiliser plus tard dans le code lors de l'appel à l'outil de récupération de Strands.
    print(f"Successfully retrieved FAQ Knowledge Base ID: {kb_id}")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'ParameterNotFound':
        print("ERROR: SSM parameter 'faq_kb_id' does not exist.")
        print("Please create the SSM parameter 'faq_kb_id' with your FAQ Knowledge Base ID before running this script.")
        sys.exit(1)
    else:
        print(f"ERROR: Failed to retrieve SSM parameter 'faq_kb_id': {str(e)}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error retrieving SSM parameter 'faq_kb_id': {str(e)}")
    sys.exit(1)
##################################

# Create a boto client config with custom settings
boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60
)

# Create a Bedrock model instance
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0", #j'ai changé le modèle pour que ca marche
    region_name=region,
    temperature=0.3,
    #top_p=0.8,     #ca me dit que claude haiku ne supporte pas top_p ET temperature, du coup j'ai commenté 1 sur les 2
    boto_client_config=boto_config,
)

@tool
def get_anycompany_docs(user_query: str) -> str:    # -> str means the function should return a string
    try:        
        # Use strands retrieve tool
        tool_use = {
            "toolUseId": "get_anycompany_docs",
            "input": {
                "text": user_query,
                "knowledgeBaseId": kb_id,           #use the kb_id retrieved from SSM Parameter Store
                "region": region,
                "numberOfResults": 3,
                "score": 0.4
            }
        }
        result = retrieve.retrieve(tool_use)

        if result["status"] == "success":
            return result["content"][0]["text"]
        else:
            return f"Unable to access technical support documentation. Error: {result['content'][0]['text']}"

    except Exception as e:
        print(f"Detailed error in get_anycompany_docs: {str(e)}")
        return f"Unable to access anycompany documentation. Error: {str(e)}"


# Create the Agent. Pass the "retrieve" tool in the tools list.
faq_agent = Agent(
    tools=[get_anycompany_docs],
    model=bedrock_model,
    system_prompt="You are a friendly agent that answers questions about AnyCompany's profile, retail policies, financial performance, annual reports, terms and conditions etc.",
)


if __name__ == "__main__":
    
    result1 = faq_agent("What is the returns policy of AnyCompany?")
    print(result1)

    result2 = faq_agent("When was AnyCompany established?")
    print(result2)

    result3 = faq_agent("What is your contact center phone number?")
    print(result3)