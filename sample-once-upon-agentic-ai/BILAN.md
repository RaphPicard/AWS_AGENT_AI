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
- Le typage des arguments (`faces: int`) est transmis à l'agent
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
- `MCPClient(transport_factory)` — le transport est une fonction qui retourne la connexion
- Le `with` statement gère le cycle de vie de la connexion
- `list_tools_sync()` découvre dynamiquement les outils disponibles côté serveur
- L'agent reçoit les outils MCP exactement comme des outils locaux

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

# Connexion au serveur MCP de dés
mcp_client = MCPClient(lambda: streamable_http_client("http://localhost:8082/mcp"))

# Découverte des agents A2A connus
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

**Points clés A2A :**
- `A2AServer(agent, port)` → expose l'agent sur le réseau
- `A2AClientToolProvider(known_agent_urls=[...])` → génère des "outils" pour contacter les agents distants
- `provider.tools` contient `a2a_list_discovered_agents` et `a2a_send_message`
- Les outils MCP et A2A se combinent simplement : `tools=mcp_tools + provider.tools`

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

## Récapitulatif des imports essentiels

```python
# Agent de base
from strands import Agent

# Outils personnalisés
from strands import tool

# Outils built-in
from strands_tools import http_request, python_repl, file_write

# MCP — serveur
from mcp.server import FastMCP

# MCP — client
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp.mcp_client import MCPClient

# A2A — serveur agent
from strands.multiagent.a2a import A2AServer

# A2A — client orchestrateur
from strands_tools.a2a_client import A2AClientToolProvider
```

---

## Ordre de démarrage des services

Pour faire tourner l'architecture complète du chapitre 5 :

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
