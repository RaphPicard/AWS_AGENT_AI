# Bilan — Workshop "Once Upon Agentic AI" (Strands SDK / AWS)

## Vue d'ensemble

Ce workshop couvre la création d'agents IA avec le **SDK Strands** (AWS), en cinq chapitres progressifs : de l'agent le plus simple jusqu'à l'orchestration multi-agents via les protocoles **MCP** et **A2A**.

---

## Concepts clés et vocabulaire

| Terme | Définition |
|---|---|
| **Agent** | Instance IA qui reçoit un prompt, raisonne, et peut appeler des outils |
| **Tool** | Fonction Python exposée à l'agent pour qu'il l'utilise de lui-même |
| **MCP** | Model Context Protocol — standard pour exposer des outils sur un serveur HTTP |
| **A2A** | Agent-to-Agent — communication entre agents distincts via HTTP |
| **LLM Provider** | Fournisseur du modèle (ici AWS Bedrock, modèle Mistral / Sonnet 4.5) |
| **System Prompt** | Instruction de rôle donnée à l'agent à l'initialisation |
| **callback_handler** | Fonction appelée à chaque événement du cycle de vie de l'agent |
| **stream_async** | Méthode de l'agent retournant un async generator pour streamer la réponse |
| **BedrockModel** | Classe Strands encapsulant un modèle Bedrock avec ses paramètres fins |
| **BotocoreConfig** | Config boto3 pour les retries, timeouts, etc. |

---

## Chapitre 1 — Agent de base (`1_strands_basics/simple_agent.py`)

### Notion : Créer et appeler un agent

```python
from strands import Agent

agent = Agent(
    system_prompt="You are a game master for a Dungeon & Dragon game."
)

response = agent("Hi, I am an adventurer ready for adventure!")
```

**Points importants :**
- `Agent(system_prompt, name, tools)` — constructeur minimal
- L'agent est appelé comme une fonction : `agent("message")`
- Le modèle sous-jacent (LLM) est configuré par défaut via les variables d'environnement AWS

### Notion : Activer les logs de debug

```python
import logging
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
```

> Permet de voir le raisonnement interne de l'agent (chain-of-thought, appels d'outils).
> Pour désactiver : repasser à `logging.ERROR`

### Notion : Agent avec modèle personnalisé et `BotocoreConfig`

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
    boto_client_config=boto_config,   # PAS directement dans BedrockModel
)

agent = Agent(model=bedrock_model)
```

**Points importants :**
- On peut aussi passer l'ID directement : `Agent(model="us.anthropic.claude-haiku-...")`
- `BotocoreConfig` se passe via `boto_client_config`, pas directement à `BedrockModel`
- Claude Haiku ne supporte pas `temperature` ET `top_p` simultanément

### Notion : Métriques d'observabilité

```python
response = agent("Tell me about agentic AI")
print(response.metrics.get_summary())   # tokens, latence, nb d'appels d'outils
```

---

## Chapitre 1 bis — Streaming (`1_strands_basics/`)

### Notion : Streaming avec async iterators (`1g`)

```python
import asyncio
from strands import Agent

async_iter_agent = Agent(
    tools=[calculator],
    callback_handler=None   # ⚠️ désactiver pour éviter le double affichage
)

async def process_streaming_response():
    agent_stream = async_iter_agent.stream_async("What is 25 * 48?")

    async for event in agent_stream:
        if "data" in event:
            print(event["data"], end="", flush=True)
        elif "current_tool_use" in event and event["current_tool_use"].get("name"):
            print(f"\n[Tool: {event['current_tool_use']['name']}]")

asyncio.run(process_streaming_response())
# En Jupyter : await process_streaming_response()  (pas asyncio.run)
```

**Points importants :**
- `stream_async()` retourne un **async generator** — chaque `event` est un dict
- Clés utiles : `"data"` (texte), `"current_tool_use"` (outil en cours)
- `callback_handler=None` est obligatoire pour le contrôle manuel du stream

### Notion : Streaming avec callback_handler (`1h`)

```python
def event_loop_tracker(**kwargs):
    if kwargs.get("init_event_loop"):    print("Event loop initialized")
    elif kwargs.get("start_event_loop"): print("Event loop cycle starting")
    elif kwargs.get("start"):            print("New cycle started")
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
agent("What is 42+7?")   # appel SYNCHRONE (pas de stream_async)
```

**Phases du cycle de vie (kwargs clés) :**
| Clé | Phase |
|---|---|
| `init_event_loop` | Initialisation |
| `start_event_loop` | Début d'un cycle |
| `start` | Nouveau cycle |
| `message` | Message créé (contient `role`) |
| `complete` | Cycle terminé |
| `force_stop` | Arrêt forcé (contient `force_stop_reason`) |
| `data` | Chunk de texte |
| `current_tool_use` | Outil en cours (contient `name`) |

**Différence async vs callback :**
- **Async iterator** : `stream_async()` + `async for` + `callback_handler=None` → contrôle total, asynchrone
- **Callback** : `callback_handler=ma_fonction` + appel synchrone → plus simple, même thread

---

## Chapitre 2 — Outils intégrés (`2_built_in_tools/`)

### Notion : Passer des outils built-in à un agent

```python
from strands import Agent
from strands_tools import http_request

agent = Agent(
    tools=[http_request]
)

agent("Using https://en.wikipedia.org/wiki/Dungeons_%26_Dragons tell me the designers.")
```

**Outils built-in disponibles dans `strands_tools` :**
- `http_request` — requêtes HTTP / scraping web
- `python_repl` — exécution de code Python à la volée
- `file_write` — écriture de fichiers sur le disque
- `calculator` — calculs mathématiques
- `current_time` — heure courante
- `retrieve` — interrogation d'une Knowledge Base Bedrock
- `use_aws` — appels API AWS génériques (DynamoDB, S3, Lambda…)

### Notion : Combiner plusieurs outils

```python
from strands_tools import python_repl, file_write

arcane_scribe = Agent(
    tools=[python_repl, file_write],
    system_prompt="You are a wizard who writes and executes code spells."
)
```

> L'agent choisit **lui-même** quel outil utiliser selon le contexte du message.

**Variable d'environnement importante :**
```bash
export BYPASS_TOOL_CONSENT=true   # désactive la demande de confirmation avant chaque appel d'outil
```

---

## Chapitre 3 — Outils personnalisés (`3_custom_tools/agent_with_dice_roll_tool.py`)

### Notion : Créer un outil avec le décorateur `@tool`

```python
from strands import Agent, tool

@tool
def roll_dice(faces: int = 6) -> int:
    """
    Roll a dice with a specified number of faces.
    """
    import random
    if faces < 1:
        raise ValueError("Dice must have at least 1 face")
    return random.randint(1, faces)

dice_master = Agent(
    tools=[roll_dice],
    system_prompt="You are Lady Luck, the mystical keeper of dice."
)
```

**Règles du décorateur `@tool` :**
- La **docstring** est obligatoire — l'agent l'utilise pour savoir quand et comment appeler l'outil
- Le typage des arguments (`faces: int`) est transmis à l'agent via le schéma JSON
- La fonction peut lever des exceptions : l'agent les gère

---

## Chapitre 4 — Intégration MCP (`4_mcp_integration/`)

### Architecture MCP

```
[Serveur MCP]  ←HTTP→  [Client MCP]  →  [Agent Strands]
  (port 8082)              (MCPClient)       (tools=mcp_tools)
```

### Notion : Créer un serveur MCP (`dice_roll_mcp_server.py`)

```python
from mcp.server import FastMCP

mcp = FastMCP(
    name="D&D Dice Roll Service",
    port=8082
)

@mcp.tool()
def roll_dice(faces: int = 6, count: int = 1) -> dict:
    """Roll multiple dice with a specified number of faces."""
    results = [random.randint(1, faces) for _ in range(count)]
    return {"results": results, "faces": faces}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

**Démarrage du serveur :**
```bash
python dice_roll_mcp_server.py
```

### Notion : Créer un client MCP et connecter l'agent (`gamemaster_mcp_client.py`)

```python
from mcp.client.streamable_http import streamable_http_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

def create_streamable_http_transport():
    return streamable_http_client("http://localhost:8082/mcp/")

streamable_http_mcp_client = MCPClient(create_streamable_http_transport)

with streamable_http_mcp_client as mcp:
    mcp_tools = mcp.list_tools_sync()       # récupère la liste des outils du serveur

    gamemaster = Agent(
        system_prompt="You are Lady Luck...",
        tools=mcp_tools                      # outils injectés depuis le serveur MCP
    )
    gamemaster("Roll a d20")
```

**Points clés MCP :**
- `MCPClient(transport_factory)` — le transport est une **fonction lambda** qui retourne la connexion
- Le `with` statement gère le cycle de vie de la connexion
- `list_tools_sync()` découvre dynamiquement les outils disponibles côté serveur
- L'agent reçoit les outils MCP exactement comme des outils locaux
- On peut mélanger outils locaux et MCP : `tools=local_tools + mcp_tools`

### Notion : MCP avec authentification Cognito (AgentCore Gateway)

```python
from mcp.client.streamable_http import streamablehttp_client  # ⚠️ sans underscore dans certaines versions

mcp_client = MCPClient(lambda: streamablehttp_client(
    agentcore_mcp_gatewayURL,
    headers={"Authorization": f"Bearer {cognito_access_token}"}  # token Cognito
))

with mcp_client:
    mcp_tools = mcp_client.list_tools_sync()
    agent = Agent(tools=[mon_tool_local] + mcp_tools)  # mix local + MCP
```

> ⚠️ **Piège** : `streamable_http_client` (avec underscore) vs `streamablehttp_client` (sans underscore) — les deux existent selon la version, vérifier l'import.

---

## Chapitre 5 — Architecture multi-agents A2A (`5_a2a_integration/`)

### Architecture globale

```
[Client utilisateur]
        ↓ HTTP POST /inquire
[Game Master Orchestrator] (port 8009)
        ↓ A2A              ↓ MCP
[Rules Agent (8000)]   [Dice Roll Server (8082)]
[Character Agent (8001)]
```

### Notion : Exposer un agent comme serveur A2A

```python
from strands import Agent, tool
from strands.multiagent.a2a import A2AServer

agent = Agent(
    description="Specialized D&D character management agent...",
    system_prompt="You are a D&D character management specialist...",
    name="Character Creator Agent",
    tools=[create_character, find_character_by_name, list_all_characters],
)

a2a_server = A2AServer(agent=agent, port=8001)

if __name__ == "__main__":
    a2a_server.serve()
```

> Chaque agent spécialisé tourne sur son propre port et expose une API A2A.

### Notion : Orchestrateur qui contacte d'autres agents (A2A + MCP)

```python
from strands_tools.a2a_client import A2AClientToolProvider
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

mcp_client = MCPClient(lambda: streamable_http_client("http://localhost:8082/mcp"))

A2A_AGENT_URLS = ["http://127.0.0.1:8000", "http://127.0.0.1:8001"]
provider = A2AClientToolProvider(known_agent_urls=A2A_AGENT_URLS)

with mcp_client:
    mcp_tools = mcp_client.list_tools_sync()

    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        name="Game Master Orchestrator",
        tools=mcp_tools + provider.tools    # outils MCP + outils A2A fusionnés
    )
```

**Outils fournis par `provider.tools` :**
- `a2a_list_discovered_agents` — liste les agents A2A disponibles avec leurs URLs
- `a2a_send_message` — envoie un message à un agent A2A via son URL

> ⚠️ **Piège** : toujours appeler `a2a_list_discovered_agents` AVANT `a2a_send_message` pour obtenir les vraies URLs. Ne jamais inventer ou hardcoder une URL dans le system prompt.

### Notion : Exposer l'orchestrateur via FastAPI

```python
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="D&D Game Master API")

@app.post("/inquire")
async def ask_agent(request: QuestionRequest):
    with mcp_client:
        response = agent(request.question)
        return JSONResponse(content={"response": str(response)})

if __name__ == "__main__":
    uvicorn.run(app, port=8009)
```

---

## Comparatif A2A vs @tool (orchestration)

| Critère | A2A (`A2AServer` / `A2AClientToolProvider`) | `@tool` wrapping |
|---|---|---|
| **Déploiement** | Chaque agent = processus séparé sur un port | Tous les agents = même processus Python |
| **Communication** | HTTP entre processus | Appel de fonction local |
| **Scalabilité** | Agents indépendants, scalables séparément | Couplé, tout tombe ensemble |
| **Complexité** | Plus complexe (ports, réseau) | Plus simple (imports Python) |
| **Ordre démarrage** | 4 terminaux séparés | 1 seul script |
| **Exemple workshop** | "Once Upon Agentic AI" chap. 5 | Retail CPG Lab 4 |

---

## Récapitulatif des imports essentiels

```python
# Agent de base
from strands import Agent

# Outils personnalisés
from strands import tool

# Outils built-in
from strands_tools import http_request, python_repl, file_write, calculator
from strands_tools import retrieve, use_aws   # KB et AWS APIs

# Modèle avec paramètres fins
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

# MCP — serveur
from mcp.server import FastMCP

# MCP — client (⚠️ deux variantes selon version)
from mcp.client.streamable_http import streamable_http_client    # avec underscore
from mcp.client.streamable_http import streamablehttp_client     # sans underscore (obsolete mais utilisé)
from strands.tools.mcp.mcp_client import MCPClient
from strands.tools.mcp import MCPClient                          # alias court

# A2A — serveur agent
from strands.multiagent.a2a import A2AServer

# A2A — client orchestrateur
from strands_tools.a2a_client import A2AClientToolProvider

# FastAPI (exposition HTTP)
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
```

---

## Clients boto3 distincts — tableau récapitulatif

| Client | Import | Utilisé pour |
|---|---|---|
| `boto3.client('bedrock')` | — | Créer/lister les guardrails |
| `boto3.client('bedrock-runtime')` | — | Tester un guardrail (`apply_guardrail`), invoquer un modèle |
| `boto3.client('ssm')` | — | Lire/écrire dans SSM Parameter Store |
| `boto3.Session().region_name` | — | Récupérer la région AWS courante |

> ⚠️ **Piège** : `bedrock` et `bedrock-runtime` sont deux clients **différents**. `bedrock` = plan de contrôle (créer des ressources). `bedrock-runtime` = plan de données (appeler le modèle, tester guardrail).

---

## Ordre de démarrage des services (Chapitre 5)

```bash
# Terminal 1 — Serveur MCP de dés
python 4_mcp_integration/dice_roll_mcp_server.py

# Terminal 2 — Agent des règles
python 5_a2a_integration/agents/rules_agent/rules_agent.py

# Terminal 3 — Agent des personnages
python 5_a2a_integration/agents/character_agent/character_agent.py

# Terminal 4 — Orchestrateur Game Master
python 5_a2a_integration/agents/gamemaster_orchestrator/gamemaster_orchestrator.py
```

---

## Variables d'environnement AWS (à redéfinir à chaque nouveau terminal)

```bash
export AWS_DEFAULT_REGION="us-west-2"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
export BYPASS_TOOL_CONSENT=true   # optionnel — évite les confirmations d'outils
```
