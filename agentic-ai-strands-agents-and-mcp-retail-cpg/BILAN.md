# Bilan — Workshop "Agentic AI with Strands Agents for Retail & CPG" (AWS)

## Vue d'ensemble

Ce workshop applique le **SDK Strands** à un cas concret de retail (entreprise fictive *AnyCompany*), en cinq labs progressifs : fondamentaux du SDK, agents FAQ connectés à une **Knowledge Base Bedrock**, agent de recherche produits avec **MCP** et **guardrails**, agent de stock via **DynamoDB**, et orchestration multi-agents. Les données (FAQ, produits, inventaire) sont stockées dans S3 / DynamoDB et exposées via des services AWS managés.

---

## Concepts clés et vocabulaire

| Terme | Définition |
|---|---|
| **Agent** | Instance Strands qui reçoit un prompt, raisonne et appelle des outils |
| **BedrockModel** | Classe Strands encapsulant un modèle Amazon Bedrock avec ses paramètres fins |
| **Knowledge Base (KB)** | Base vectorielle Bedrock permettant la recherche sémantique sur des documents |
| **retrieve** | Outil built-in `strands_tools.retrieve` pour interroger une KB Bedrock |
| **use_aws** | Outil built-in `strands_tools.use_aws` pour appeler n'importe quelle API AWS |
| **SSM Parameter Store** | Service AWS (Systems Manager) utilisé pour stocker la config (IDs, URLs, tokens) hors code |
| **MCP** | Model Context Protocol — protocole standard pour exposer des outils sur un serveur HTTP |
| **AgentCore Gateway** | Proxy AWS managé qui expose un serveur MCP avec authentification Cognito |
| **Guardrail** | Filtre Bedrock (topics, mots, contenu) appliqué aux entrées/sorties d'un agent |
| **Orchestrateur** | Agent qui reçoit d'autres agents comme outils et route les requêtes |
| **callback_handler** | Fonction appelée à chaque événement du cycle de vie de l'agent (streaming, outils…) |
| **FAQ** | Foire Aux Questions — ici, questions sur les politiques et profil d'AnyCompany |
| **CPG** | Consumer Packaged Goods — biens de consommation courante |

---

## Lab 0 — Fondamentaux (`lab-0/fundamentals/`)

### Notion : Agent minimal sans configuration (`1a-simple-agent.py`)

```python
from strands import Agent

agent = Agent()                          # modèle par défaut via variables d'env AWS
response = agent("Tell me about agentic AI")
print(response)
```

**Points importants :**
- `Agent()` sans argument utilise le modèle par défaut configuré via les credentials AWS
- L'agent se comporte comme une fonction : `agent("message")`

---

### Notion : Agent avec modèle personnalisé par ID (`1b-agent-with-custom-model.py`)

```python
agent = Agent(
    model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    system_prompt="You are a helpful assistant..."
)
```

**Points importants :**
- On peut passer directement l'ID de modèle Bedrock en string au lieu d'un objet `BedrockModel`
- Le préfixe `us.` indique le routage cross-region AWS

---

### Notion : Paramètres fins avec `BedrockModel` et `BotocoreConfig` (`1c-agent-with-model-params.py`)

```python
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

boto_config = BotocoreConfig(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=5,
    read_timeout=30
)

bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name=region,
    temperature=0.3,
    boto_client_config=boto_config,
)

agent = Agent(model=bedrock_model)
```

**Points importants :**
- `BedrockModel` permet de contrôler `temperature`, `top_p`, timeouts et retries
- Claude Haiku ne supporte pas `temperature` ET `top_p` simultanément — commenter l'un des deux
- `BotocoreConfig` se passe via `boto_client_config`, pas directement à `BedrockModel`

---

### Notion : Logs de debug (`1d-agents-with-debug-logging.py`)

```python
import logging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
```

**Points importants :**
- `logging.getLogger("strands").setLevel(logging.DEBUG)` active la trace complète (chain-of-thought, appels d'outils)
- Pour désactiver : repasser à `logging.ERROR`
- À configurer **avant** la création de l'agent pour capturer toute l'initialisation

---

### Notion : Outils built-in et custom (`1e-agent-with-tools.py`)

```python
from strands import Agent, tool
from strands_tools import http_request, calculator, current_time

@tool
def letter_counter(word: str, letter: str) -> int:
    """
    Count occurrences of a specific letter in a word.

    Args:
        word (str): The input word to search in
        letter (str): The specific letter to count
    """
    return word.lower().count(letter.lower())

agent = Agent(tools=[calculator, current_time, http_request, letter_counter])
```

**Points importants :**
- La **docstring** est obligatoire et doit décrire précisément les args — l'agent s'en sert pour savoir quand appeler l'outil
- Le **typage des paramètres** (`word: str`) est transmis au modèle via le schéma JSON
- L'agent choisit **lui-même** l'outil à utiliser selon le contexte ; on ne l'appelle pas directement

---

### Notion : Métriques d'observabilité (`1f-observability.py`)

```python
response = agent("Tell me about agentic AI")

print(response.metrics.get_summary())   # tokens, latence, nombre d'appels d'outils
```

**Points importants :**
- `response.metrics.get_summary()` retourne un dict JSON avec le résumé d'utilisation
- Utile pour mesurer les coûts (tokens input/output) et la performance

---

### Notion : Streaming async avec itérateurs (`1g-realtime-streaming-async-iterators.py`)

```python
import asyncio
from strands import Agent

async_iter_agent = Agent(
    tools=[calculator],
    callback_handler=None   # désactive le handler par défaut
)

async def process_streaming_response():
    agent_stream = async_iter_agent.stream_async("What is 25 * 48?")

    async for event in agent_stream:
        if "data" in event:
            print(event["data"], end="", flush=True)         # chunk de texte
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            print(f"\n[Tool: {event['current_tool_use']['name']}]")  # appel d'outil

asyncio.run(process_streaming_response())
```

**Points importants :**
- `callback_handler=None` est nécessaire pour éviter le double affichage lors d'un streaming manuel
- `stream_async()` retourne un **async generator** — chaque `event` est un dict
- Clés d'event utiles : `"data"` (texte), `"current_tool_use"` (outil en cours)
- Dans un Jupyter notebook : utiliser `await` au lieu de `asyncio.run()`

---

### Notion : Streaming avec `callback_handler` (`1h-realtime-streaming-callback.py`)

```python
def event_loop_tracker(**kwargs):
    if kwargs.get("init_event_loop"):
        print("Event loop initialized")
    elif "message" in kwargs:
        print(f"New message: {kwargs['message']['role']}")
    elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
        print(f"Using tool: {kwargs['current_tool_use']['name']}")
    if "data" in kwargs:
        print(kwargs["data"], end="", flush=True)

agent = Agent(
    tools=[calculator],
    callback_handler=event_loop_tracker
)
agent("What is 42+7?")
```

**Points importants :**
- Le callback reçoit `**kwargs` — les clés présentes varient selon la phase du cycle de vie
- Phases clés : `init_event_loop`, `start_event_loop`, `start`, `message`, `complete`, `force_stop`
- Contrairement au streaming async, l'agent est appelé de façon **synchrone** (`agent("msg")`)

---

## Lab 1a — FAQ Agent via Console Bedrock (`lab-1a/faq-agent/`)

### Notion : Agent Bedrock natif (sans code Strands)

Ce lab se fait **entièrement dans la console AWS** (Amazon Bedrock > Agents > Create Agent). On crée :
1. Une **Knowledge Base** alimentée par les documents AnyCompany stockés dans S3
2. Un **Agent Bedrock** qui interroge cette KB pour répondre aux questions FAQ

**Points importants :**
- Aucun code Python — c'est une approche no-code/low-code via l'interface Bedrock
- Le **Knowledge Base ID** créé ici est réutilisé dans tous les labs suivants → le noter
- Architecture : Console → Bedrock Agent Builder → Knowledge Base → S3 (documents)

---

## Lab 1b — FAQ Agent avec Strands (`lab-1b/faq_strands-agent/faq_strands_agent.py`)

### Notion : Lire la configuration depuis SSM Parameter Store

```python
import boto3
ssm_client = boto3.client('ssm', region_name=region)
response = ssm_client.get_parameter(Name="faq_kb_id")
kb_id = response['Parameter']['Value']
```

**Points importants :**
- SSM Parameter Store = alternative sécurisée au hardcoding des IDs en clair dans le code
- Le paramètre `faq_kb_id` doit exister avant de lancer le script (créé lors du lab 1a)
- Erreur courante : `ParameterNotFound` → vérifier le nom exact du paramètre dans la console

---

### Notion : Outil custom wrappant l'outil `retrieve` de Strands

```python
from strands_tools import retrieve
from strands.tools import tool

@tool
def get_anycompany_docs(user_query: str) -> str:
    """Recherche dans la Knowledge Base AnyCompany."""
    tool_use = {
        "toolUseId": "get_anycompany_docs",
        "input": {
            "text": user_query,
            "knowledgeBaseId": kb_id,     # ID récupéré depuis SSM
            "region": region,
            "numberOfResults": 3,
            "score": 0.4                  # seuil de score de pertinence minimum
        }
    }
    result = retrieve.retrieve(tool_use)

    if result["status"] == "success":
        return result["content"][0]["text"]
    else:
        return f"Erreur: {result['content'][0]['text']}"

faq_agent = Agent(
    tools=[get_anycompany_docs],
    model=bedrock_model,
    system_prompt="You are a friendly agent that answers questions about AnyCompany..."
)
```

**Points importants :**
- `strands_tools.retrieve` est l'outil built-in Strands pour interroger une KB Bedrock
- On l'enveloppe dans un `@tool` custom pour pouvoir lui passer le `knowledgeBaseId` dynamiquement
- `score=0.4` : ne retourner que les résultats avec un score de pertinence ≥ 0.4
- Le résultat est dans `result["content"][0]["text"]` — toujours vérifier `result["status"]` d'abord

---

## Lab 2a — Product Search Agent + MCP via AgentCore Gateway (`lab-2/product-search-agent-with-mcp-tools/`)

### Notion : MCPClient avec authentification Bearer (AgentCore Gateway)

```python
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# Connexion au serveur MCP via AgentCore Gateway avec token Cognito
streamable_http_mcp_client = MCPClient(
    lambda: streamablehttp_client(
        agentcore_mcp_gatewayURL,
        headers={"Authorization": f"Bearer {anycomp_agcore_gw_cognito_accesstoken}"}
    )
)

with streamable_http_mcp_client:
    mcp_tools = streamable_http_mcp_client.list_tools_sync()

    product_search_agent = Agent(
        tools=[get_products_from_kb, mcp_tools],  # KB + outils MCP fusionnés
        model=_bedrock_model,
        system_prompt=system_prompt
    )
    result = str(product_search_agent(input_query))
```

**Points importants :**
- `AgentCore Gateway` = proxy AWS qui expose un serveur MCP (ici : service d'avis produits) avec auth Cognito
- L'URL du gateway et le token Cognito sont récupérés depuis **SSM Parameter Store** (voir lab 1b)
- Les outils MCP (`mcp_tools`) et les outils locaux (`get_products_from_kb`) se combinent simplement en liste
- L'agent est **recréé à chaque appel** à l'intérieur du `with` block car la connexion MCP est éphémère
- Note : `streamablehttp_client` (sans underscore dans lab 2) vs `streamable_http_client` (avec underscore dans lab 4) — les deux existent dans la lib, préférer `streamablehttp_client`

---

### Notion : Paramètres SSM nécessaires pour le lab 2a

```python
prod_search_kb_id          = ssm_client.get_parameter(Name="product_search_kb_id")
prod_search_agent_model_id = ssm_client.get_parameter(Name="prod_search_agent_model_id")
agentcore_mcp_gatewayURL   = ssm_client.get_parameter(Name="anycomp_prod_reviews_mcp_server_url")
cognito_token              = ssm_client.get_parameter(Name="anycomp_agcore_gw_cognito_accesstoken")
```

**Points importants :**
- `prod_search_agent_model_id` est **écrit** dans SSM via `put_parameter(Overwrite=True)` au démarrage pour s'assurer d'avoir la bonne valeur
- Si `agentcore_mcp_gatewayURL == "NOT CONFIGURED"` → le gateway n'a pas été créé dans la console (prérequis du lab)

---

## Lab 2b — Product Search Agent + Guardrails Bedrock (`lab-2/product-search-agent-with-guardrails/`)

### Notion : Créer un guardrail Bedrock programmatiquement

```python
bedrock_client = boto3.client('bedrock')

response = bedrock_client.create_guardrail(
    name='product-specific-restrictions',
    topicPolicyConfig={
        'topicsConfig': [{'name': 'Product restrictions', 'type': 'DENY', ...}]
    },
    contentPolicyConfig={
        'filtersConfig': [
            {'type': 'SEXUAL',  'inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
            {'type': 'VIOLENCE','inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
            {'type': 'PROMPT_ATTACK', 'inputStrength': 'HIGH', 'outputStrength': 'NONE'},
        ]
    },
    wordPolicyConfig={
        'wordsConfig': [{'text': 'counterfeit'}, {'text': 'fake'}, ...],
        'managedWordListsConfig': [{'type': 'PROFANITY'}]
    },
    blockedInputMessaging='Je ne peux pas traiter cette demande.',
    blockedOutputsMessaging='Je ne peux pas fournir cette réponse.',
)
guardrail_id = response['guardrailId']
```

**Points importants :**
- Toujours vérifier si le guardrail existe déjà (`list_guardrails()`) avant d'en créer un nouveau
- La version par défaut d'un guardrail créé est `"DRAFT"`
- Trois types de politiques : **topics** (sujets à bloquer), **content** (filtres de contenu), **words** (mots interdits)
- `PROMPT_ATTACK` : mettre `outputStrength: 'NONE'` (l'attaque est à l'entrée, pas à la sortie)

---

### Notion : Attacher un guardrail à un `BedrockModel`

```python
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name=region,
    guardrail_id=guardrail_id,
    guardrail_version="DRAFT",
    guardrail_trace="enabled",    # log les interventions du guardrail
    temperature=0.3,
)

agent_with_guardrail = Agent(
    system_prompt=_system_prompt,
    model=bedrock_model,
    tools=[get_products_from_kb]
)
response = agent_with_guardrail(prompt)

# Vérifier si le guardrail a bloqué la réponse
if hasattr(response, 'stop_reason') and response.stop_reason == "guardrail_intervened":
    print("GUARDRAIL INTERVENED!")
```

**Points importants :**
- Le guardrail est attaché au **modèle**, pas à l'agent — il filtre toutes les interactions du modèle
- `guardrail_trace="enabled"` permet de voir dans les logs quelle règle a été déclenchée
- `response.stop_reason == "guardrail_intervened"` permet de détecter programmatiquement un blocage

---

### Notion : Tester un guardrail directement sans agent

```python
bedrock_runtime = boto3.client('bedrock-runtime')

response = bedrock_runtime.apply_guardrail(
    guardrailIdentifier=guardrail_id,
    guardrailVersion="DRAFT",
    source='INPUT',   # ou 'OUTPUT'
    content=[{"text": {"text": "le texte à tester"}}]
)

is_blocked = response.get('action') == 'GUARDRAIL_INTERVENED'
```

**Points importants :**
- `bedrock-runtime` (avec tiret), pas `bedrock` — client différent pour les appels runtime
- Tester `'INPUT'` et `'OUTPUT'` séparément pour diagnostiquer d'où vient le blocage
- `response['assessments'][0]['topicPolicy']['topics']` liste les topics déclenchés

---

## Lab 3 — Inventory Agent (`lab-3/inventory-agent-strand/inventory_agent.py`)

### Notion : Appeler DynamoDB via l'outil `use_aws`

```python
from strands_tools import use_aws

# Agent auxiliaire dédié aux appels AWS
aws_agent = Agent(tools=[use_aws])

@tool
def get_product(product_id: str):
    """
    Use this tool when you need to get the details of a product to
    see if that's available in stock or not.

    Args:
        product_id: The id of the product
    """
    result = aws_agent.tool.use_aws(
        service_name="dynamodb",
        operation_name="get_item",
        parameters={
            "TableName": "anycompany_product_inventory",
            "Key": {"product_id": {"S": product_id}}
        },
        region=region,
        label="Get One Item"
    )
    return result

inventory_agent = Agent(
    model=model,
    tools=[get_product],
    system_prompt="You are an Agent that checks if a product is available in the inventory..."
)
```

**Points importants :**
- `use_aws` = outil built-in Strands qui encapsule **toute l'API AWS** (DynamoDB, S3, Lambda, etc.)
- Le pattern est un **double agent** : `aws_agent` (interne, accès AWS) est wrappé dans un `@tool` pour `inventory_agent` (métier)
- `aws_agent.tool.use_aws(...)` appelle l'outil **directement** sans passer par le LLM — c'est un appel programmatique
- Le `label` est juste pour le logging, il n'affecte pas le comportement
- La clé DynamoDB doit être fournie avec son type Bedrock : `{"S": product_id}` pour une string

---

## Lab 4 — Orchestrateur multi-agents (`lab-4/search_orchestrator_agent/Orchestrator.py`)

### Architecture globale

```
[Utilisateur]
      ↓
[Orchestrator] (Orchestrator.py)
      ↓ @tool              ↓ @tool              ↓ @tool
[faq_agent_tool]  [product_search_agent_tool]  [inventory_agent_tool]
      ↓                    ↓                         ↓
[FAQAgent.py]       [ProductSearchAgent.py]    [InventoryAgent.py]
  (KB Bedrock)        (KB + MCP AgentCore)       (DynamoDB)
```

### Notion : Exposer un agent spécialisé comme outil de l'orchestrateur

```python
# Importer les agents des modules Python précédents
from FAQAgent import faq_agent
from ProductSearchAgent import product_search_agent    # fonction, pas l'objet Agent
from InventoryAgent import inventory_agent

# Wrapper chaque agent dans un @tool pour que l'orchestrateur puisse les appeler
@tool
def faq_agent_tool(query: str) -> str:
    """
    Answers questions about AnyCompany.
    Use this tool for general questions about policies, procedures, or common inquiries.
    ...
    """
    return faq_agent(query)

@tool
def product_search_agent_tool(query: str) -> str:
    """Discovers products for customers based on their requirements. ..."""
    return product_search_agent(query)   # product_search_agent est une FONCTION dans ProductSearchAgent.py

@tool
def inventory_agent_tool(query: str) -> str:
    """Checks the inventory of products. ..."""
    return inventory_agent(query)
```

**Points importants :**
- Le pattern clé : chaque agent spécialisé devient un **outil** de l'orchestrateur via `@tool`
- `FAQAgent.py` expose l'objet `faq_agent` directement → appelé comme `faq_agent(query)`
- `ProductSearchAgent.py` expose une **fonction** `product_search_agent()` (pas l'objet Agent) → gère en interne la connexion MCP
- `InventoryAgent.py` expose l'objet `inventory_agent` → appelé comme `inventory_agent(query)`
- La **docstring de chaque `@tool`** est critique : c'est ce que l'orchestrateur lit pour décider quel agent appeler

---

### Notion : Créer l'orchestrateur

```python
orchestrator = Agent(
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    tools=[faq_agent_tool, product_search_agent_tool, inventory_agent_tool],
    model=bedrock_model
)

# Exemple de requête complexe combinant plusieurs agents
result = orchestrator(
    "I want a midi dress available in stock — show product reviews too."
)
```

**Points importants :**
- L'orchestrateur raisonne seul sur **l'ordre et le choix** des agents à appeler
- Le `ORCHESTRATOR_SYSTEM_PROMPT` précise explicitement quelle règle pour chaque outil (ex: "FAQ Agent does NOT have product availability info")
- Une requête peut déclencher **plusieurs outils en séquence** : d'abord product search, puis inventory
- L'orchestrateur synthétise les réponses de tous les agents dans une réponse finale cohérente

---

## Récapitulatif des imports essentiels

```python
# Agent de base
from strands import Agent
from strands import tool                                # décorateur @tool

# Modèle avec paramètres fins
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

# Outils built-in
from strands_tools import retrieve       # Knowledge Base Bedrock
from strands_tools import use_aws        # API AWS génériques (DynamoDB, S3…)
from strands_tools import http_request, calculator, current_time

# MCP — client
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client   # noter l'absence d'underscore

# AWS SDK
import boto3

# Guardrails (clients distincts)
bedrock_client  = boto3.client('bedrock')          # créer/lister les guardrails
bedrock_runtime = boto3.client('bedrock-runtime')  # tester un guardrail, invoquer un modèle
ssm_client      = boto3.client('ssm')              # lire la configuration
```

---

## Paramètres SSM à créer avant de lancer les labs

| Paramètre SSM | Contenu | Utilisé dans |
|---|---|---|
| `faq_kb_id` | ID de la Knowledge Base FAQ | Lab 1b, Lab 4 |
| `product_search_kb_id` | ID de la Knowledge Base produits | Lab 2, Lab 4 |
| `prod_search_agent_model_id` | ID du modèle Bedrock (écrit par le code) | Lab 2, Lab 4 |
| `anycomp_prod_reviews_mcp_server_url` | URL du gateway AgentCore MCP | Lab 2, Lab 4 |
| `anycomp_agcore_gw_cognito_accesstoken` | Token Cognito pour le gateway | Lab 2, Lab 4 |

---

## Variables d'environnement AWS (à redéfinir à chaque nouveau terminal)

```bash
export AWS_DEFAULT_REGION="us-west-2"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
export BYPASS_TOOL_CONSENT=true   # évite les confirmations avant chaque appel d'outil
```

> Pour charger les credentials depuis le `.env` à la racine du projet :
> ```bash
> source ../../.env && python3 <script.py>
> ```

---

## Ordre de lancement pour le lab 4

```bash
# Un seul script suffit — il importe les agents spécialisés et lance l'orchestrateur
python Orchestrator.py
```

> Contrairement à une architecture A2A (lab "Once Upon Agentic AI"), ici les agents spécialisés **ne tournent pas sur des ports séparés** — ils sont importés comme modules Python dans le même process que l'orchestrateur.
