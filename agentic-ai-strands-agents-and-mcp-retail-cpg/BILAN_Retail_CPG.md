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
| **Orchestrateur** | Agent qui reçoit d'autres agents comme outils `@tool` et route les requêtes |
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

import json
print(json.dumps(response.metrics.get_summary(), indent=4))
```

**Points importants :**
- `response.metrics.get_summary()` retourne un dict JSON avec le résumé d'utilisation
- Contient : tokens input/output, latence, nombre d'appels d'outils
- Utile pour mesurer les coûts et la performance

---

### Notion : Streaming async avec itérateurs (`1g-realtime-streaming-async-iterators.py`)

```python
import asyncio
from strands import Agent

async_iter_agent = Agent(
    tools=[calculator],
    callback_handler=None   # ⚠️ désactive le handler par défaut
)

async def process_streaming_response():
    agent_stream = async_iter_agent.stream_async("What is 25 * 48?")

    async for event in agent_stream:
        if "data" in event:
            print(event["data"], end="", flush=True)         # chunk de texte
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            print(f"\n[Tool: {event['current_tool_use']['name']}]")  # appel d'outil

asyncio.run(process_streaming_response())
# En Jupyter notebook : await process_streaming_response()
```

**Points importants :**
- `callback_handler=None` est nécessaire pour éviter le double affichage lors d'un streaming manuel
- `stream_async()` retourne un **async generator** — chaque `event` est un dict
- Clés d'event utiles : `"data"` (texte), `"current_tool_use"` (outil en cours)

---

### Notion : Streaming avec `callback_handler` (`1h-realtime-streaming-callback.py`)

```python
def event_loop_tracker(**kwargs):
    if kwargs.get("init_event_loop"):    print("Event loop initialized")
    elif kwargs.get("start_event_loop"): print("Event loop cycle starting")
    elif "message" in kwargs:            print(f"New message: {kwargs['message']['role']}")
    elif kwargs.get("complete"):         print("Cycle completed")
    elif kwargs.get("force_stop"):       print(f"Force stop: {kwargs.get('force_stop_reason')}")

    if "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
        print(f"Using tool: {kwargs['current_tool_use']['name']}")

    if "data" in kwargs:
        print(kwargs["data"], end="", flush=True)

agent = Agent(
    tools=[calculator],
    callback_handler=event_loop_tracker
)
agent("What is 42+7?")   # appel SYNCHRONE (pas stream_async)
```

**Phases du cycle de vie :**
| Clé kwargs | Signification |
|---|---|
| `init_event_loop` | Initialisation de l'event loop |
| `start_event_loop` | Début d'un cycle |
| `start` | Nouveau cycle démarré |
| `message` | Message créé (`kwargs['message']['role']`) |
| `complete` | Cycle terminé |
| `force_stop` | Arrêt forcé (`kwargs['force_stop_reason']`) |
| `data` | Chunk de texte généré |
| `current_tool_use` | Outil en cours (`kwargs['current_tool_use']['name']`) |

**Différence async vs callback :**
- **Async iterator** : `stream_async()` + `async for` + `callback_handler=None` → contrôle total, asynchrone
- **Callback** : `callback_handler=ma_fonction` + appel synchrone → plus simple, même thread

---

## Lab 1a — FAQ Agent via Console Bedrock (`lab-1a/faq-agent/`)

### Notion : Agent Bedrock natif (sans code Strands)

Ce lab se fait **entièrement dans la console AWS** (Amazon Bedrock > Agents > Create Agent). On crée :
1. Une **Knowledge Base** alimentée par les documents AnyCompany stockés dans S3
2. Un **Agent Bedrock** qui interroge cette KB pour répondre aux questions FAQ

**Points importants :**
- Aucun code Python — approche no-code/low-code via l'interface Bedrock
- Le **Knowledge Base ID** créé ici est réutilisé dans tous les labs suivants → le noter
- Architecture : Console → Bedrock Agent Builder → Knowledge Base → S3 (documents)

---

## Lab 1b — FAQ Agent avec Strands (`lab-1b/faq_strands-agent/faq_strands_agent.py`)

### Notion : Lire une config depuis SSM Parameter Store

```python
import boto3
from botocore.exceptions import ClientError

ssm_client = boto3.client('ssm', region_name=region)

try:
    response = ssm_client.get_parameter(Name="faq_kb_id")
    kb_id = response['Parameter']['Value']
except ClientError as e:
    if e.response['Error']['Code'] == 'ParameterNotFound':
        print("ERROR: SSM parameter 'faq_kb_id' does not exist.")
        sys.exit(1)
```

**Points importants :**
- SSM = AWS Systems Manager → Application Tools → Parameter Store dans la console
- Permet de stocker des IDs/URLs/tokens **hors du code** — jamais en dur dans le script
- `get_parameter(Name=...)['Parameter']['Value']` pour lire
- `put_parameter(Name=..., Value=..., Type='String', Overwrite=True)` pour écrire/mettre à jour

---

### Notion : Outil `retrieve` pour interroger une Knowledge Base

```python
from strands import Agent, tool
from strands_tools import retrieve

@tool
def get_anycompany_docs(user_query: str) -> str:
    """
    Use this tool to find answers about AnyCompany policies.

    Args:
        user_query: The user's question
    """
    tool_use = {
        "toolUseId": "get_anycompany_docs",
        "input": {
            "text": user_query,
            "knowledgeBaseId": kb_id,      # ID récupéré depuis SSM
            "region": region,
            "numberOfResults": 3,          # nombre de chunks retournés
            "score": 0.4                   # seuil de pertinence min (0-1)
        }
    }
    result = retrieve.retrieve(tool_use)

    if result["status"] == "success":
        return result["content"][0]["text"]
    else:
        return f"Error: {result['content'][0]['text']}"

faq_agent = Agent(
    tools=[get_anycompany_docs],
    model=bedrock_model,
    system_prompt="You are a friendly agent that answers questions about AnyCompany..."
)
```

**Points importants :**
- `retrieve` est un outil built-in Strands qui encapsule l'API Bedrock Knowledge Base
- Le dict `tool_use` avec `toolUseId` et `input` est la structure attendue par `retrieve.retrieve()`
- `score=0.4` = seuil de similarité cosinus — en dessous, les résultats sont rejetés
- `numberOfResults=3` = nombre de chunks de documents retournés
- L'outil `@tool` wrappant `retrieve` permet à l'agent de savoir **quand** l'utiliser (via la docstring)

---

## Lab 2 — Product Search Agent avec MCP et Guardrails (`lab-2/`)

### Notion : MCP avec authentification Cognito (AgentCore Gateway)

```python
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client  # ⚠️ sans underscore

# Récupération du token et de l'URL depuis SSM
agentcore_mcp_gatewayURL = ssm_client.get_parameter(Name="anycomp_prod_reviews_mcp_server_url")['Parameter']['Value']
cognito_token = ssm_client.get_parameter(Name="anycomp_agcore_gw_cognito_accesstoken")['Parameter']['Value']

# Client MCP avec header d'authentification Bearer
mcp_client = MCPClient(lambda: streamablehttp_client(
    agentcore_mcp_gatewayURL,
    headers={"Authorization": f"Bearer {cognito_token}"}
))

def product_search_agent(input_query):
    with mcp_client:
        mcp_tools = mcp_client.list_tools_sync()   # découverte dynamique des outils

        agent = Agent(
            tools=[get_products_from_kb] + mcp_tools,  # ⚠️ mix @tool local + liste MCP
            model=_bedrock_model,
            system_prompt=system_prompt
        )
        return str(agent(input_query))
```

**Points importants :**
- Le token Cognito s'injecte dans le header HTTP `Authorization: Bearer <token>`
- L'URL du gateway et le token sont **toujours dans SSM** — jamais hardcodés
- `tools=[mon_tool_local] + mcp_tools` — on peut mélanger un `@tool` custom et une liste MCP
- L'agent et le `with mcp_client` doivent être dans la **même portée** (même bloc `with`)
- `AgentCore Gateway` = proxy AWS managé qui authentifie et route vers Lambda

**Architecture AgentCore Gateway :**
```
Agent Strands
    ↓ MCPClient (Bearer token Cognito)
AgentCore Gateway (AWS managé)
    ↓ authentifie via Cognito
Lambda (cfn-retrieve-product-reviews)
    ↓
DynamoDB (product reviews)
```

---

### Notion : Créer un guardrail Bedrock

```python
bedrock_client = boto3.client('bedrock')   # client plan de CONTRÔLE

def create_guardrail():
    # 1. Vérifier si le guardrail existe déjà
    list_response = bedrock_client.list_guardrails()
    for g in list_response.get('guardrails', []):
        if g.get('name') == 'product-specific-restrictions':
            return g.get('id'), "DRAFT"

    # 2. Créer le guardrail
    response = bedrock_client.create_guardrail(
        name='product-specific-restrictions',
        description='Prevents recommendations on specific products.',
        topicPolicyConfig={
            'topicsConfig': [
                {
                    'name': 'HateSpeech',
                    'definition': 'Content promoting hate or discrimination',
                    'examples': ['nazi symbol', 'racist content'],
                    'type': 'DENY'
                }
            ]
        },
        wordPolicyConfig={
            'wordsConfig': [
                {'text': 'lolita'},
                {'text': 'dupe'}
            ]
        },
        contentPolicyConfig={
            'filtersConfig': [
                {'type': 'HATE', 'inputStrength': 'HIGH', 'outputStrength': 'HIGH'}
            ]
        },
        blockedInputMessaging='Input blocked. Please modify your request.',
        blockedOutputsMessaging='Output blocked. Please modify your request.',
    )
    return response.get('guardrailId'), "DRAFT"
```

---

### Notion : Attacher un guardrail à un agent

```python
bedrock_model_with_guardrail = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name=region,
    guardrail_id=guardrail_id,          # ⚠️ attaché au MODÈLE, pas à l'agent
    guardrail_version=guardrail_version,
    guardrail_trace="enabled",          # logs des règles déclenchées
    temperature=0.3,
)

agent_with_guardrail = Agent(
    system_prompt=_system_prompt,
    model=bedrock_model_with_guardrail,
    tools=[get_products_from_kb]
)

response = agent_with_guardrail("Find me a t-shirt with a nazi symbol")

# Détecter programmatiquement un blocage
if hasattr(response, 'stop_reason') and response.stop_reason == "guardrail_intervened":
    print("⚠️ GUARDRAIL INTERVENED!")
```

**Points importants :**
- Le guardrail est attaché au **modèle** (`BedrockModel`), pas à l'agent — filtre toutes les interactions
- `guardrail_trace="enabled"` → logs détaillés des règles déclenchées
- `response.stop_reason == "guardrail_intervened"` → détection programmatique du blocage

---

### Notion : Tester un guardrail directement sans agent

```python
bedrock_runtime = boto3.client('bedrock-runtime')   # ⚠️ client plan de DONNÉES (avec tiret)

response = bedrock_runtime.apply_guardrail(
    guardrailIdentifier=guardrail_id,
    guardrailVersion="DRAFT",
    source='INPUT',   # ou 'OUTPUT'
    content=[{"text": {"text": "le texte à tester"}}]
)

is_blocked = response.get('action') == 'GUARDRAIL_INTERVENED'

# Topics déclenchés
if is_blocked:
    assessments = response.get('assessments', [])
    blocked_topics = [t.get('name') for t in
                      assessments[0]['topicPolicy'].get('topics', [])
                      if t.get('action') == 'BLOCKED']
```

**Points importants :**
- `bedrock-runtime` (avec tiret) ≠ `bedrock` — deux clients distincts pour deux plans distincts
- Tester `source='INPUT'` et `source='OUTPUT'` séparément pour diagnostiquer
- `response['assessments'][0]['topicPolicy']['topics']` liste les topics bloqués

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
    result = aws_agent.tool.use_aws(          # appel PROGRAMMATIQUE (pas via LLM)
        service_name="dynamodb",
        operation_name="get_item",
        parameters={
            "TableName": "anycompany_product_inventory",
            "Key": {"product_id": {"S": product_id}}  # ⚠️ type DynamoDB : {"S": valeur}
        },
        region=region,
        label="Get One Item"                  # juste pour le logging
    )
    return result

inventory_agent = Agent(
    model=model,
    tools=[get_product],
    system_prompt="""
You are an Agent that checks if a product is available in the inventory.
Return output in the below JSON format. Do not include any other text.
{
    "product_id" : PRODUCT_ID,
    "in_stock": IN_STOCK_VALUE
}
where IN_STOCK_VALUE = "yes" if quantity_available is > 0 and "no" otherwise.
"""
)
```

**Points importants :**
- `use_aws` = outil built-in Strands qui encapsule **toute l'API AWS** (DynamoDB, S3, Lambda, etc.)
- Pattern **double agent** : `aws_agent` (interne, accès AWS brut) wrappé dans un `@tool` pour `inventory_agent` (métier)
- `aws_agent.tool.use_aws(...)` = appel **programmatique** direct — bypass le LLM
- La clé DynamoDB doit être typée : `{"S": product_id}` pour une String, `{"N": "42"}` pour Number
- Le `label` est juste pour le logging, n'affecte pas le comportement

---

## Lab 4 — Orchestrateur multi-agents (`lab-4/search_orchestrator_agent/Orchestrator.py`)

### Architecture globale

```
[Utilisateur]
      ↓
[Orchestrator] (Orchestrator.py) — 1 seul processus Python
      ↓ @tool              ↓ @tool                  ↓ @tool
[faq_agent_tool]  [product_search_agent_tool]  [inventory_agent_tool]
      ↓                    ↓                         ↓
[FAQAgent.py]       [ProductSearchAgent.py]    [InventoryAgent.py]
  (KB Bedrock)        (KB + MCP AgentCore)       (DynamoDB)
```

### Notion : Exposer un agent spécialisé comme outil de l'orchestrateur

```python
# Importer les agents des modules Python
from FAQAgent import faq_agent                       # objet Agent importé directement
from ProductSearchAgent import product_search_agent  # FONCTION (pas l'objet Agent)
from InventoryAgent import inventory_agent           # objet Agent importé directement

@tool
def faq_agent_tool(query: str) -> str:
    """
    Answers questions about AnyCompany.
    Use this tool for general questions about policies, procedures, or common inquiries.
    Do NOT use for product availability or product search.

    Args:
        query: The search question. (String)
    """
    return faq_agent(query)    # objet Agent appelé comme fonction

@tool
def product_search_agent_tool(query: str) -> str:
    """
    Discovers products for customers based on their requirements.
    Use this tool when you need to discover products based on customer requirements.
    """
    return product_search_agent(query)   # FONCTION qui gère en interne la connexion MCP

@tool
def inventory_agent_tool(query: str) -> str:
    """
    Checks the inventory of products.
    Use this tool to check if a specific product is available in stock.
    """
    return inventory_agent(query)
```

**Points importants :**
- `FAQAgent.py` expose l'objet `faq_agent` → appelé comme `faq_agent(query)`
- `ProductSearchAgent.py` expose une **fonction** `product_search_agent()` — elle crée l'agent ET gère la connexion MCP en interne, à chaque appel
- `InventoryAgent.py` expose l'objet `inventory_agent` → appelé comme `inventory_agent(query)`
- La **docstring de chaque `@tool`** est critique : c'est ce que lit l'orchestrateur pour router

---

### Notion : Créer l'orchestrateur

```python
orchestrator = Agent(
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    tools=[faq_agent_tool, product_search_agent_tool, inventory_agent_tool],
    model=bedrock_model
)

result = orchestrator("I want a midi dress available in stock — show product reviews too.")
```

**Points importants :**
- L'orchestrateur raisonne seul sur **l'ordre et le choix** des agents à appeler
- Le `ORCHESTRATOR_SYSTEM_PROMPT` précise les règles : ex. "FAQ Agent does NOT have product availability info"
- Une requête peut déclencher **plusieurs outils en séquence** : product search → inventory
- Contrairement à A2A, tous les agents tournent dans le **même processus Python** (lancement = `python Orchestrator.py`)

---

## Comparatif A2A vs @tool (orchestration)

| Critère | A2A (`A2AServer` / `A2AClientToolProvider`) | `@tool` wrapping (Lab 4) |
|---|---|---|
| **Déploiement** | Chaque agent = processus séparé sur un port | Tous les agents = même processus Python |
| **Communication** | HTTP entre processus | Appel de fonction local |
| **Scalabilité** | Agents indépendants, scalables séparément | Couplé, tout tombe ensemble |
| **Complexité** | Plus complexe (ports, réseau) | Plus simple (imports Python) |
| **Ordre de lancement** | 4 terminaux séparés | 1 seul script |
| **Exemple workshop** | "Once Upon Agentic AI" chap. 5 | Retail CPG Lab 4 |

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

# MCP — client (⚠️ deux variantes selon version)
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client   # sans underscore (version Retail)
from mcp.client.streamable_http import streamable_http_client  # avec underscore (version D&D)

# AWS SDK
import boto3

# Clients boto3 distincts
bedrock_client  = boto3.client('bedrock')          # plan CONTRÔLE : créer/lister guardrails
bedrock_runtime = boto3.client('bedrock-runtime')  # plan DONNÉES : apply_guardrail, invoquer modèle
ssm_client      = boto3.client('ssm')              # lire/écrire SSM Parameter Store
```

---

## Clients boto3 — tableau récapitulatif

| Client | Utilisé pour | Méthodes clés |
|---|---|---|
| `boto3.client('bedrock')` | Plan de contrôle | `create_guardrail()`, `list_guardrails()` |
| `boto3.client('bedrock-runtime')` | Plan de données | `apply_guardrail()`, `invoke_model()` |
| `boto3.client('ssm')` | Config sécurisée | `get_parameter()`, `put_parameter()` |

> ⚠️ **Piège fréquent** : `bedrock` ≠ `bedrock-runtime` — deux clients différents. `apply_guardrail` est sur `bedrock-runtime`, pas sur `bedrock`.

---

## Paramètres SSM à créer avant de lancer les labs

| Paramètre SSM | Contenu | Utilisé dans |
|---|---|---|
| `faq_kb_id` | ID de la Knowledge Base FAQ | Lab 1b, Lab 4 |
| `product_search_kb_id` | ID de la Knowledge Base produits | Lab 2, Lab 4 |
| `prod_search_agent_model_id` | ID du modèle Bedrock (écrit par le code avec `put_parameter`) | Lab 2, Lab 4 |
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

# Charger depuis un .env :
source ../../.env && python3 <script.py>
```

---

## Ordre de lancement pour le lab 4

```bash
# Un seul script suffit — il importe les agents spécialisés comme modules Python
python Orchestrator.py
```

> Contrairement à A2A, les agents spécialisés **ne tournent pas sur des ports séparés** — ils sont importés comme modules dans le même processus.
