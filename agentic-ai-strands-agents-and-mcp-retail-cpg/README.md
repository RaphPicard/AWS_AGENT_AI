# Agentic AI with Strands Agents for Retail & CPG 

This workshop demonstrates how to build intelligent AI agents for retail and consumer packaged goods (CPG) applications using Strands Agents and AWS services. Learn how to create specialized agents that can answer questions, search products, check inventory, and collaborate to solve complex customer queries.

## Workshop Structure

### Prerequisites
- Sample data for loading into S3 and DynamoDB.

### Lab 0: Fundamentals
Comprehensive introduction to Strands Agents framework:
- Basic agent creation and model configuration
- Tool integration and custom tool development
- Advanced patterns including async operations and callback handling
- Observability, monitoring, and debugging techniques
- Multi-modal capabilities and guardrail implementation

### Lab 1: FAQ Agents
Two approaches to building FAQ systems:
- **Lab 1a**: Console-based agent using Amazon Bedrock Agent Builder
- **Lab 1b**: Code-first approach with Strands Agents and Knowledge Base integration

### Lab 2: Product Search Agent
AI-powered shopping assistant Agent with advanced capabilities:
- Product discovery and recommendation engine
- Bedrock Knowledge Base integration for semantic search
- Content safety through guardrails implementation
- External service integration via MCP (Model Context Protocol)
- Product review aggregation and analysis

### Lab 3: Inventory Agent
Real-time inventory check Agent:
- Stock availability checking

### Lab 4: Search Orchestrator Agent
Multi-agent collaboration and intelligent routing:
- Centralized orchestration of specialized agents
- Intent recognition and query routing
- Agent coordination and response aggregation
- Scalable multi-agent architecture patterns

## Key Technologies

- **Amazon Bedrock**: Foundation models for natural language understanding
- **Strands Agents**: Code-first framework for building AI agents
- **Amazon Bedrock Knowledge Base**: Vector database for semantic search
- **Amazon DynamoDB**: NoSQL database for product and inventory data
- **Model Context Protocol (MCP)**: Standard for agent-tool communication

## Getting Started

1. Start with `lab-0/fundamentals`
3. Progress through Labs 0-4 in sequence

## Requirements

- AWS account with access to Amazon Bedrock
- Python 3.11+
