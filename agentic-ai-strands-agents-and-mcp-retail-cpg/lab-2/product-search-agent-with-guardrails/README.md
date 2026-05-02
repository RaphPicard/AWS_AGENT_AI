In this tutorial we will create Product Search Strands Agent that:

Uses Amazon Bedrock Knowledge Base to search for products using natural language queries
Integrates with a MCP server through AgentCore Gateway for fetching product reviews

# Product Search Strands Agent

This lab demonstrates how to build an AI shopping assistant that helps customers discover products and reviews using a Knowledge Base and MCP (Model Context Protocol) tools. The agent uses Amazon Bedrock models through the Strands framework and integrates with Bedrock AgentCore Gateway to access product review services.

## Architecture
![Bedrock FAQ Agent Architecture](product-search-architecture-with-guardrails.png)


# Running the code
View the code `productsearchagent-agentcore-gw-mcp.py` and `productsearchagent-guardrail.py`. Run using the below commands -

```
python productsearchagent-agentcore-gw-mcp.py

python productsearchagent-guardrail.py
```